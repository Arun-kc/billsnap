import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class LineItemBase(BaseModel):
    item_name: str | None = None
    hsn_code: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    gst_rate: float | None = None
    sort_order: int = 0


class LineItemCreate(LineItemBase):
    pass


class LineItemUpdate(LineItemBase):
    id: uuid.UUID | None = None  # None = create new


class LineItemOut(LineItemBase):
    id: uuid.UUID
    bill_id: uuid.UUID
    model_config = {"from_attributes": True}


class BillSummary(BaseModel):
    id: uuid.UUID
    vendor_name: str | None
    bill_date: date | None
    total_amount: float | None
    category: str | None
    document_type: str
    is_verified: bool
    extraction_confidence: float | None
    thumbnail_url: str | None = None
    model_config = {"from_attributes": True}


class BillDetail(BillSummary):
    vendor_gstin: str | None
    bill_number: str | None
    taxable_amount: float | None
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    user_notes: str | None
    image_url: str | None = None
    line_items: list[LineItemOut] = []
    created_at: datetime
    updated_at: datetime
    # True when OCR failed to read the bill and the user must type it in manually
    # (e.g. illegible handwritten bill). UI should render a manual-entry form.
    needs_manual_entry: bool = False


class BillUpdate(BaseModel):
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    bill_number: str | None = None
    bill_date: date | None = None
    document_type: str | None = None
    category: str | None = None
    total_amount: float | None = None
    taxable_amount: float | None = None
    cgst_amount: float | None = None
    sgst_amount: float | None = None
    igst_amount: float | None = None
    is_verified: bool | None = None
    user_notes: str | None = None
    line_items: list[LineItemUpdate] | None = None  # None = don't touch; [] = clear all


class PaginationOut(BaseModel):
    page: int
    per_page: int
    total: int


class MonthlySummary(BaseModel):
    total_amount: float
    total_cgst: float
    total_sgst: float
    total_igst: float
    bill_count: int
    unverified_count: int


class BillListOut(BaseModel):
    bills: list[BillSummary]
    pagination: PaginationOut
    summary: MonthlySummary


class DashboardMonth(BaseModel):
    month: str  # YYYY-MM
    bill_count: int
    total_amount: float
    total_tax: float
    unverified_count: int


class DashboardOut(BaseModel):
    months: list[DashboardMonth]
