import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user, get_db
from ..models.user import User
from ..models.ocr_job import OcrJob
from ..schemas.bill import BillDetail, BillListOut, BillSummary, BillUpdate, MonthlySummary, PaginationOut
from ..schemas.ocr_job import UploadResponse
from ..services import bill_service, storage_service

router = APIRouter(prefix="/api/v1", tags=["bills"])

_ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/bills/upload", status_code=status.HTTP_202_ACCEPTED, response_model=UploadResponse)
async def upload_bill(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{content_type}'. Upload a JPEG or PNG image.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File exceeds the 10 MB limit.",
        )

    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    job_id = uuid.uuid4()

    # Upload to storage
    file_key = storage_service.upload_bill(
        user_id=current_user.id,
        job_id=job_id,
        file_bytes=file_bytes,
        content_type=content_type,
        ext=ext,
    )

    # Create OCR job — worker picks it up within poll_interval seconds
    job = OcrJob(
        id=job_id,
        user_id=current_user.id,
        original_file_key=file_key,
        file_content_type=content_type,
        file_size_bytes=len(file_bytes),
    )
    db.add(job)
    await db.commit()

    return UploadResponse(
        job_id=job_id,
        status="pending",
        message="Bill uploaded. Processing will begin shortly.",
    )


@router.get("/bills", response_model=BillListOut)
async def list_bills(
    month: str | None = Query(None, description="Filter by month, e.g. 2026-04"),
    verified: bool | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bills, total, summary = await bill_service.list_bills(
        db, current_user.id, month=month, verified=verified,
        category=category, page=page, per_page=per_page,
    )

    bill_summaries = []
    for bill in bills:
        job = bill.ocr_job if hasattr(bill, "ocr_job") else None
        thumb_key = job.thumbnail_key if job else None
        bill_summaries.append(BillSummary(
            id=bill.id,
            vendor_name=bill.vendor_name,
            bill_date=bill.bill_date,
            total_amount=float(bill.total_amount) if bill.total_amount else None,
            category=bill.category,
            document_type=bill.document_type,
            is_verified=bill.is_verified,
            extraction_confidence=float(bill.extraction_confidence) if bill.extraction_confidence else None,
            thumbnail_url=storage_service.signed_url(thumb_key),
        ))

    return BillListOut(
        bills=bill_summaries,
        pagination=PaginationOut(page=page, per_page=per_page, total=total),
        summary=MonthlySummary(**summary),
    )


@router.get("/bills/export")
async def export_bills(
    month: str = Query(..., description="Month to export, e.g. 2026-04"),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import Response
    from ..services import export_service

    if format == "xlsx":
        data = await export_service.generate_excel(db, current_user.id, month)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="bills_{month}.xlsx"'},
        )
    else:
        data = await export_service.generate_csv(db, current_user.id, month)
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="bills_{month}.csv"'},
        )


@router.get("/bills/{bill_id}", response_model=BillDetail)
async def get_bill(
    bill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = await bill_service.get_bill(db, bill_id)
    if not bill or bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    thumb_key = bill.ocr_job.thumbnail_key if bill.ocr_job else None
    orig_key = bill.ocr_job.original_file_key if bill.ocr_job else None

    return BillDetail(
        id=bill.id,
        vendor_name=bill.vendor_name,
        vendor_gstin=bill.vendor_gstin,
        bill_number=bill.bill_number,
        bill_date=bill.bill_date,
        document_type=bill.document_type,
        category=bill.category,
        total_amount=float(bill.total_amount) if bill.total_amount else None,
        taxable_amount=float(bill.taxable_amount) if bill.taxable_amount else None,
        cgst_amount=float(bill.cgst_amount),
        sgst_amount=float(bill.sgst_amount),
        igst_amount=float(bill.igst_amount),
        is_verified=bill.is_verified,
        user_notes=bill.user_notes,
        extraction_confidence=float(bill.extraction_confidence) if bill.extraction_confidence else None,
        thumbnail_url=storage_service.signed_url(thumb_key),
        image_url=storage_service.signed_url(orig_key),
        line_items=[
            {
                "id": li.id, "bill_id": li.bill_id, "item_name": li.item_name,
                "hsn_code": li.hsn_code, "quantity": float(li.quantity) if li.quantity else None,
                "unit": li.unit, "unit_price": float(li.unit_price) if li.unit_price else None,
                "total_price": float(li.total_price) if li.total_price else None,
                "gst_rate": float(li.gst_rate) if li.gst_rate else None,
                "sort_order": li.sort_order,
            }
            for li in bill.line_items
        ],
        created_at=bill.created_at,
        updated_at=bill.updated_at,
    )


@router.patch("/bills/{bill_id}", response_model=BillDetail)
async def update_bill(
    bill_id: uuid.UUID,
    payload: BillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = await bill_service.get_bill(db, bill_id)
    if not bill or bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    bill = await bill_service.update_bill(db, bill, payload, current_user.id)
    # Re-fetch to return updated detail
    return await get_bill(bill_id, db, current_user)


@router.delete("/bills/{bill_id}", status_code=status.HTTP_200_OK)
async def delete_bill(
    bill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bill = await bill_service.get_bill(db, bill_id)
    if not bill or bill.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Clean up storage
    if bill.ocr_job:
        try:
            storage_service.delete(bill.ocr_job.original_file_key)
            if bill.ocr_job.thumbnail_key:
                storage_service.delete(bill.ocr_job.thumbnail_key)
        except Exception:
            pass  # Storage cleanup is best-effort

    await bill_service.delete_bill(db, bill, current_user.id)
    return {"message": "Bill deleted.", "id": str(bill_id)}
