"""
Unit tests for app.services.bill_service.

Pure utility functions (_parse_date, _float_or_none) are tested directly.
Functions that require a DB session use a mocked AsyncSession.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.bill import BillUpdate
from app.services.bill_service import (
    _float_or_none,
    _parse_date,
    create_from_ocr,
    delete_bill,
    get_bill,
    list_bills,
    update_bill,
)
from tests.conftest import BILL_ID, USER_ID, make_bill, make_mock_db, make_mock_result, make_ocr_job


# ---------------------------------------------------------------------------
# _parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_valid_iso(self):
        assert _parse_date("2026-04-10") == date(2026, 4, 10)

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_null_string_returns_none(self):
        assert _parse_date("null") is None

    def test_invalid_format_returns_none(self):
        assert _parse_date("10-04-2026") is None

    def test_garbage_returns_none(self):
        assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# _float_or_none
# ---------------------------------------------------------------------------

class TestFloatOrNone:
    def test_number_string(self):
        assert _float_or_none("1234.56") == 1234.56

    def test_integer(self):
        assert _float_or_none(500) == 500.0

    def test_none_returns_none(self):
        assert _float_or_none(None) is None

    def test_empty_string_returns_none(self):
        assert _float_or_none("") is None

    def test_null_string_returns_none(self):
        assert _float_or_none("null") is None

    def test_zero(self):
        assert _float_or_none(0) == 0.0

    def test_invalid_string_returns_none(self):
        assert _float_or_none("abc") is None


# ---------------------------------------------------------------------------
# create_from_ocr
# ---------------------------------------------------------------------------

class TestCreateFromOcr:
    @pytest.fixture
    def extracted(self):
        return {
            "document_type": "tax_invoice",
            "vendor_name": "Kerala Electricals",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "bill_number": "INV-001",
            "bill_date": "2026-04-10",
            "total_amount": 1180.0,
            "taxable_amount": 1000.0,
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
            "igst_amount": None,
            "category": "Electrical Supplies",
            "line_items": [
                {"description": "Wire 2.5mm", "hsn_code": "8544", "quantity": 10, "unit": "m", "unit_price": 50.0, "amount": 500.0}
            ],
        }

    async def test_creates_bill_with_correct_vendor(self, extracted):
        db = make_mock_db()
        job = make_ocr_job()

        created_bill = make_bill(vendor_name="Kerala Electricals")
        db.refresh = AsyncMock(side_effect=lambda b: None)

        with patch("app.services.bill_service.Bill") as MockBill, \
             patch("app.services.bill_service.LineItem") as MockLineItem:
            MockBill.return_value = created_bill
            MockLineItem.return_value = MagicMock()

            result = await create_from_ocr(db, job, extracted, confidence=0.90)

        assert db.add.called
        assert db.commit.called

    async def test_creates_line_items(self, extracted):
        db = make_mock_db()
        job = make_ocr_job()
        bill = make_bill()

        with patch("app.services.bill_service.Bill") as MockBill, \
             patch("app.services.bill_service.LineItem") as MockLineItem:
            MockBill.return_value = bill
            mock_li = MagicMock()
            MockLineItem.return_value = mock_li

            await create_from_ocr(db, job, extracted, confidence=0.90)

        # One LineItem add call for the one line item
        assert MockLineItem.called

    async def test_credit_note_uses_credit_amount(self):
        db = make_mock_db()
        job = make_ocr_job()
        bill = make_bill(total_amount=500.0)

        extracted = {
            "document_type": "credit_note",
            "vendor_name": "Vendor",
            "document_number": "CN-001",
            "document_date": "2026-04-10",
            "credit_amount": 500.0,
        }

        with patch("app.services.bill_service.Bill") as MockBill, \
             patch("app.services.bill_service.LineItem"):
            MockBill.return_value = bill
            await create_from_ocr(db, job, extracted, confidence=0.80)

        # credit_amount should be mapped to total_amount
        call_kwargs = MockBill.call_args.kwargs
        assert call_kwargs["total_amount"] == 500.0
        assert call_kwargs["document_type"] == "credit_note"

    async def test_none_confidence_stored_as_none(self):
        db = make_mock_db()
        job = make_ocr_job()
        bill = make_bill(extraction_confidence=None)

        extracted = {"document_type": "tax_invoice", "vendor_name": "V"}

        with patch("app.services.bill_service.Bill") as MockBill, \
             patch("app.services.bill_service.LineItem"):
            MockBill.return_value = bill
            await create_from_ocr(db, job, extracted, confidence=None)

        call_kwargs = MockBill.call_args.kwargs
        assert call_kwargs["extraction_confidence"] is None


# ---------------------------------------------------------------------------
# get_bill
# ---------------------------------------------------------------------------

class TestGetBill:
    async def test_returns_bill_when_found(self):
        bill = make_bill()
        db = make_mock_db()
        db.execute.return_value = make_mock_result(scalar=bill)

        result = await get_bill(db, BILL_ID)
        assert result is bill

    async def test_returns_none_when_not_found(self):
        db = make_mock_db()
        db.execute.return_value = make_mock_result(scalar=None)

        result = await get_bill(db, uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# list_bills
# ---------------------------------------------------------------------------

class TestListBills:
    async def test_returns_bills_and_summary(self):
        bill = make_bill()
        db = make_mock_db()

        # First execute: count query
        count_result = make_mock_result(scalar_one=1)
        # Second execute: bills query
        bills_result = make_mock_result(rows=[bill])
        # Third execute: aggregation summary
        agg_row = MagicMock()
        agg_row.total_amount = 1180.0
        agg_row.total_cgst = 90.0
        agg_row.total_sgst = 90.0
        agg_row.total_igst = 0.0
        agg_row.bill_count = 1
        agg_row.unverified_count = 1
        agg_result = make_mock_result()
        agg_result.one.return_value = agg_row

        db.execute.side_effect = [count_result, bills_result, agg_result]

        bills, total, summary = await list_bills(db, USER_ID, month="2026-04")

        assert total == 1
        assert len(bills) == 1
        assert summary["bill_count"] == 1
        assert summary["total_amount"] == 1180.0

    async def test_empty_result(self):
        db = make_mock_db()

        count_result = make_mock_result(scalar_one=0)
        bills_result = make_mock_result(rows=[])
        agg_row = MagicMock()
        agg_row.total_amount = 0
        agg_row.total_cgst = 0
        agg_row.total_sgst = 0
        agg_row.total_igst = 0
        agg_row.bill_count = 0
        agg_row.unverified_count = 0
        agg_result = make_mock_result()
        agg_result.one.return_value = agg_row

        db.execute.side_effect = [count_result, bills_result, agg_result]

        bills, total, summary = await list_bills(db, USER_ID)

        assert total == 0
        assert bills == []
        assert summary["bill_count"] == 0


# ---------------------------------------------------------------------------
# update_bill
# ---------------------------------------------------------------------------

class TestUpdateBill:
    async def test_updates_vendor_name(self):
        bill = make_bill(vendor_name="Old Vendor")
        db = make_mock_db()

        payload = BillUpdate(vendor_name="New Vendor")
        db.refresh = AsyncMock(side_effect=lambda b: setattr(b, "vendor_name", "New Vendor"))

        result = await update_bill(db, bill, payload, USER_ID)

        assert bill.vendor_name == "New Vendor"
        assert db.commit.called

    async def test_sets_is_verified(self):
        bill = make_bill(is_verified=False)
        db = make_mock_db()

        payload = BillUpdate(is_verified=True)
        await update_bill(db, bill, payload, USER_ID)

        assert bill.is_verified is True

    async def test_noop_when_no_changes(self):
        bill = make_bill(vendor_name="Same Vendor")
        db = make_mock_db()

        payload = BillUpdate()  # all None → no field updates
        await update_bill(db, bill, payload, USER_ID)

        assert db.commit.called  # audit log still gets written


# ---------------------------------------------------------------------------
# delete_bill
# ---------------------------------------------------------------------------

class TestDeleteBill:
    async def test_deletes_and_commits(self):
        bill = make_bill()
        db = make_mock_db()

        await delete_bill(db, bill, USER_ID)

        db.delete.assert_called_once_with(bill)
        db.commit.assert_called_once()
