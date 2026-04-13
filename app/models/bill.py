import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    ocr_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ocr_jobs.id"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Vendor (OCR-extracted, user-editable)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Identity (OCR-extracted, user-editable)
    bill_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bill_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False, default="tax_invoice")
    # tax_invoice | bill_of_supply | credit_note | debit_note | receipt | other
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Amounts in INR (OCR-extracted, user-editable)
    total_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    taxable_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cgst_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    # Review state
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="bills")  # noqa: F821
    ocr_job: Mapped["OcrJob"] = relationship(back_populates="bill")  # noqa: F821
    line_items: Mapped[list["LineItem"]] = relationship(  # noqa: F821
        back_populates="bill", cascade="all, delete-orphan", order_by="LineItem.sort_order"
    )
