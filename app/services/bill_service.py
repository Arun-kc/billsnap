"""
Bill CRUD service — creates bills from OCR results, handles review updates, audit logging.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.audit_log import AuditLog
from ..models.bill import Bill
from ..models.line_item import LineItem
from ..models.ocr_job import OcrJob
from ..schemas.bill import BillUpdate


def _parse_date(val: str | None) -> date | None:
    if not val or val == "null":
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        return None


def _float_or_none(val) -> float | None:
    if val is None or val == "null" or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


async def create_from_ocr(
    db: AsyncSession,
    job: OcrJob,
    extracted: dict,
    confidence: float | None,
) -> Bill:
    """Create a Bill (and its LineItems) from an OCR extraction result."""
    doc_type = extracted.get("document_type", "tax_invoice")

    # For credit notes the fields have slightly different names
    is_credit = doc_type in ("credit_note", "debit_note")
    bill_number = extracted.get("document_number" if is_credit else "bill_number")
    bill_date_str = extracted.get("document_date" if is_credit else "bill_date")
    total_amount = _float_or_none(
        extracted.get("credit_amount" if is_credit else "total_amount")
    )

    bill = Bill(
        ocr_job_id=job.id,
        user_id=job.user_id,
        vendor_name=extracted.get("vendor_name"),
        vendor_gstin=extracted.get("vendor_gstin"),
        bill_number=bill_number,
        bill_date=_parse_date(bill_date_str),
        document_type=doc_type,
        category=extracted.get("category"),
        total_amount=total_amount,
        taxable_amount=_float_or_none(extracted.get("taxable_amount")),
        cgst_amount=_float_or_none(extracted.get("cgst_amount")) or 0,
        sgst_amount=_float_or_none(extracted.get("sgst_amount")) or 0,
        igst_amount=_float_or_none(extracted.get("igst_amount")) or 0,
        extraction_confidence=confidence,
    )
    db.add(bill)
    await db.flush()  # get bill.id before inserting line items

    raw_items = extracted.get("line_items") or []
    for idx, item in enumerate(raw_items):
        line = LineItem(
            bill_id=bill.id,
            item_name=item.get("description") or item.get("item_name"),
            hsn_code=item.get("hsn_code"),
            quantity=_float_or_none(item.get("quantity")),
            unit=item.get("unit"),
            unit_price=_float_or_none(item.get("unit_price")),
            total_price=_float_or_none(item.get("amount") or item.get("total_price")),
            gst_rate=_float_or_none(item.get("gst_rate")),
            sort_order=idx,
        )
        db.add(line)

    await db.flush()
    await _audit(db, job.user_id, "bill", bill.id, "create")
    await db.commit()
    await db.refresh(bill)
    return bill


async def get_bill(db: AsyncSession, bill_id: uuid.UUID) -> Bill | None:
    result = await db.execute(
        select(Bill)
        .where(Bill.id == bill_id)
        .options(selectinload(Bill.line_items), selectinload(Bill.ocr_job))
    )
    return result.scalar_one_or_none()


async def list_bills(
    db: AsyncSession,
    user_id: uuid.UUID,
    month: str | None = None,
    verified: bool | None = None,
    category: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Bill], int, dict]:
    q = select(Bill).where(Bill.user_id == user_id).options(selectinload(Bill.ocr_job))

    if month:
        try:
            y, m = int(month[:4]), int(month[5:7])
            q = q.where(
                func.date_trunc("month", Bill.bill_date) == date(y, m, 1)
            )
        except (ValueError, IndexError):
            pass

    if verified is not None:
        q = q.where(Bill.is_verified == verified)

    if category:
        q = q.where(Bill.category == category)

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    q = q.order_by(Bill.bill_date.desc().nullslast(), Bill.created_at.desc())
    q = q.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    bills = list(result.scalars().all())

    # Summary aggregation
    agg = await db.execute(
        select(
            func.coalesce(func.sum(Bill.total_amount), 0).label("total_amount"),
            func.coalesce(func.sum(Bill.cgst_amount), 0).label("total_cgst"),
            func.coalesce(func.sum(Bill.sgst_amount), 0).label("total_sgst"),
            func.coalesce(func.sum(Bill.igst_amount), 0).label("total_igst"),
            func.count(Bill.id).label("bill_count"),
            func.count(Bill.id).filter(Bill.is_verified == False).label("unverified_count"),  # noqa: E712
        ).select_from(
            select(Bill).where(Bill.user_id == user_id)
            .where(*(
                [func.date_trunc("month", Bill.bill_date) == date(y, m, 1)]
                if month else [True]
            ))
            .subquery()
        )
    )
    row = agg.one()
    summary = {
        "total_amount": float(row.total_amount),
        "total_cgst": float(row.total_cgst),
        "total_sgst": float(row.total_sgst),
        "total_igst": float(row.total_igst),
        "bill_count": row.bill_count,
        "unverified_count": row.unverified_count,
    }
    return bills, total, summary


async def update_bill(
    db: AsyncSession,
    bill: Bill,
    payload: BillUpdate,
    user_id: uuid.UUID,
) -> Bill:
    changes: dict = {}
    scalar_fields = [
        "vendor_name", "vendor_gstin", "bill_number", "bill_date", "document_type",
        "category", "total_amount", "taxable_amount", "cgst_amount", "sgst_amount",
        "igst_amount", "is_verified", "user_notes",
    ]
    for field in scalar_fields:
        new_val = getattr(payload, field)
        if new_val is not None:
            old_val = getattr(bill, field)
            if old_val != new_val:
                changes[field] = {"old": str(old_val), "new": str(new_val)}
                setattr(bill, field, new_val)

    # Replace line items if provided
    if payload.line_items is not None:
        for li in bill.line_items:
            await db.delete(li)
        await db.flush()

        for idx, item in enumerate(payload.line_items):
            line = LineItem(
                bill_id=bill.id,
                item_name=item.item_name,
                hsn_code=item.hsn_code,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                total_price=item.total_price,
                gst_rate=item.gst_rate,
                sort_order=idx,
            )
            db.add(line)
        changes["line_items"] = {"old": "replaced", "new": f"{len(payload.line_items)} items"}

    await _audit(db, user_id, "bill", bill.id, "update", changes)
    await db.commit()
    await db.refresh(bill)
    return bill


async def delete_bill(db: AsyncSession, bill: Bill, user_id: uuid.UUID) -> None:
    await _audit(db, user_id, "bill", bill.id, "delete")
    await db.delete(bill)
    await db.commit()


async def _audit(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    entity_type: str,
    entity_id: uuid.UUID,
    action: str,
    changes: dict | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=changes,
    )
    db.add(log)
