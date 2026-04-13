from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user, get_db
from ..models.bill import Bill
from ..models.user import User
from ..schemas.bill import DashboardMonth, DashboardOut

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(
    months: int = Query(3, ge=1, le=12, description="Number of recent months to include"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            func.to_char(Bill.bill_date, "YYYY-MM").label("month"),
            func.count(Bill.id).label("bill_count"),
            func.coalesce(func.sum(Bill.total_amount), 0).label("total_amount"),
            func.coalesce(func.sum(Bill.cgst_amount + Bill.sgst_amount + Bill.igst_amount), 0).label("total_tax"),
            func.count(Bill.id).filter(Bill.is_verified == False).label("unverified_count"),  # noqa: E712
        )
        .where(Bill.user_id == current_user.id)
        .where(Bill.bill_date.isnot(None))
        .group_by(text("month"))
        .order_by(text("month DESC"))
        .limit(months)
    )
    rows = result.all()

    return DashboardOut(
        months=[
            DashboardMonth(
                month=row.month,
                bill_count=row.bill_count,
                total_amount=float(row.total_amount),
                total_tax=float(row.total_tax),
                unverified_count=row.unverified_count,
            )
            for row in rows
        ]
    )
