import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class OcrJob(Base):
    __tablename__ = "ocr_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Job state
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # pending | processing | completed | failed | needs_review | needs_manual_entry
    model_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="haiku")

    # File info
    original_file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # OCR output
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    extraction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_ocr_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Retry state
    retry_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="ocr_jobs")  # noqa: F821
    bill: Mapped["Bill | None"] = relationship(back_populates="ocr_job")  # noqa: F821
