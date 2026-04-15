"""
Shared fixtures for BillSnap tests.

Strategy: no real database required. All tests use mocked SQLAlchemy sessions
and mocked dependencies so the suite runs without PostgreSQL or Anthropic credits.
"""

import uuid
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user, get_db
from app.main import app


# ---------------------------------------------------------------------------
# Entity factories
# Use SimpleNamespace so tests can set/read attributes freely without
# triggering SQLAlchemy mapper instrumentation (which requires a live session).
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
BILL_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
JOB_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def make_user(**kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", USER_ID),
        name=kwargs.get("name", "Test Owner"),
        phone=kwargs.get("phone", "9999999999"),
        role=kwargs.get("role", "owner"),
        is_active=kwargs.get("is_active", True),
        pin_hash=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
        bills=[],
        ocr_jobs=[],
    )


def make_bill(**kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", BILL_ID),
        user_id=kwargs.get("user_id", USER_ID),
        ocr_job_id=kwargs.get("ocr_job_id", JOB_ID),
        vendor_name=kwargs.get("vendor_name", "Kerala Electricals"),
        vendor_gstin=kwargs.get("vendor_gstin", None),
        bill_number=kwargs.get("bill_number", "INV-001"),
        bill_date=kwargs.get("bill_date", date(2026, 4, 10)),
        document_type=kwargs.get("document_type", "tax_invoice"),
        category=kwargs.get("category", "Electrical Supplies"),
        total_amount=kwargs.get("total_amount", 1180.0),
        taxable_amount=kwargs.get("taxable_amount", 1000.0),
        cgst_amount=kwargs.get("cgst_amount", 90.0),
        sgst_amount=kwargs.get("sgst_amount", 90.0),
        igst_amount=kwargs.get("igst_amount", 0.0),
        is_verified=kwargs.get("is_verified", False),
        extraction_confidence=kwargs.get("extraction_confidence", 0.90),
        user_notes=kwargs.get("user_notes", None),
        original_file_key=kwargs.get("original_file_key", f"bills/{USER_ID}/{JOB_ID}/original.jpg"),
        thumbnail_key=kwargs.get("thumbnail_key", None),
        ocr_job=kwargs.get("ocr_job", None),
        line_items=kwargs.get("line_items", []),
        created_at=datetime(2026, 4, 10, 10, 0, 0),
        updated_at=datetime(2026, 4, 10, 10, 0, 0),
    )


def make_ocr_job(**kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", JOB_ID),
        user_id=kwargs.get("user_id", USER_ID),
        status=kwargs.get("status", "pending"),
        model_tier=kwargs.get("model_tier", "haiku"),
        original_file_key=f"bills/{USER_ID}/{JOB_ID}/original.jpg",
        thumbnail_key=None,
        file_content_type="image/jpeg",
        file_size_bytes=102400,
        extraction_confidence=None,
        extraction_notes=None,
        raw_ocr_response=None,
        error_message=None,
        retry_count=0,
        max_retries=2,
        started_at=None,
        completed_at=None,
        created_at=datetime(2026, 4, 10, 10, 0, 0),
        updated_at=datetime(2026, 4, 10, 10, 0, 0),
    )


def make_line_item(bill_id: uuid.UUID | None = None, **kwargs):
    return SimpleNamespace(
        id=kwargs.get("id", uuid.uuid4()),
        bill_id=bill_id or BILL_ID,
        item_name=kwargs.get("item_name", "Wire 2.5mm"),
        hsn_code=kwargs.get("hsn_code", "8544"),
        quantity=kwargs.get("quantity", 10.0),
        unit=kwargs.get("unit", "m"),
        unit_price=kwargs.get("unit_price", 50.0),
        total_price=kwargs.get("total_price", 500.0),
        gst_rate=kwargs.get("gst_rate", 18.0),
        sort_order=kwargs.get("sort_order", 0),
    )


# ---------------------------------------------------------------------------
# Database mock helpers
# ---------------------------------------------------------------------------

def make_mock_result(rows=None, scalar=None, scalar_one=None):
    """Build a MagicMock that mimics a SQLAlchemy Result."""
    result = MagicMock()
    result.all.return_value = rows or []
    result.scalars.return_value.all.return_value = rows or []
    result.scalar_one_or_none.return_value = scalar
    result.scalar_one.return_value = scalar_one if scalar_one is not None else (len(rows) if rows else 0)
    result.one.return_value = scalar_one
    return result


def make_mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=make_mock_result())
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user() -> User:
    return make_user()


@pytest.fixture
def mock_db() -> AsyncMock:
    return make_mock_db()


@pytest.fixture
def sample_bill() -> Bill:
    return make_bill()


@pytest.fixture
def sample_job() -> OcrJob:
    return make_ocr_job()


@pytest.fixture
async def api_client(user):
    """Async HTTP client with auth dependency overridden."""
    async def _get_db():
        yield make_mock_db()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
