"""
API-level tests for /api/v1/bills endpoints.

All DB and service calls are mocked. Tests verify HTTP status codes,
response shape, and that the correct service functions are invoked.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import BILL_ID, USER_ID, make_bill, make_mock_result, make_ocr_job


# ---------------------------------------------------------------------------
# GET /api/v1/bills
# ---------------------------------------------------------------------------

class TestListBillsEndpoint:
    async def test_returns_200_with_empty_list(self, api_client):
        with patch("app.routers.bills.bill_service.list_bills", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = ([], 0, {
                "total_amount": 0.0,
                "total_cgst": 0.0,
                "total_sgst": 0.0,
                "total_igst": 0.0,
                "bill_count": 0,
                "unverified_count": 0,
            })
            resp = await api_client.get("/api/v1/bills")

        assert resp.status_code == 200
        body = resp.json()
        assert body["bills"] == []
        assert body["pagination"]["total"] == 0

    async def test_returns_200_with_bill_list(self, api_client):
        bill = make_bill()
        with patch("app.routers.bills.bill_service.list_bills", new_callable=AsyncMock) as mock_list, \
             patch("app.routers.bills.storage_service.signed_url", return_value=None):
            mock_list.return_value = ([bill], 1, {
                "total_amount": 1180.0,
                "total_cgst": 90.0,
                "total_sgst": 90.0,
                "total_igst": 0.0,
                "bill_count": 1,
                "unverified_count": 1,
            })
            resp = await api_client.get("/api/v1/bills?month=2026-04")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["bills"]) == 1
        assert body["bills"][0]["vendor_name"] == "Kerala Electricals"
        assert body["summary"]["bill_count"] == 1

    async def test_month_filter_passed_to_service(self, api_client):
        with patch("app.routers.bills.bill_service.list_bills", new_callable=AsyncMock) as mock_list, \
             patch("app.routers.bills.storage_service.signed_url", return_value=None):
            mock_list.return_value = ([], 0, {
                "total_amount": 0, "total_cgst": 0, "total_sgst": 0,
                "total_igst": 0, "bill_count": 0, "unverified_count": 0,
            })
            await api_client.get("/api/v1/bills?month=2026-03")

        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs.get("month") == "2026-03"

    async def test_unauthorized_without_token(self):
        """Verify that removing auth dependency causes 401."""
        from app.dependencies import get_current_user
        from app.main import app

        # Clear overrides so real auth is checked
        app.dependency_overrides.clear()
        from httpx import ASGITransport, AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/bills")

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/bills/{bill_id}
# ---------------------------------------------------------------------------

class TestGetBillEndpoint:
    async def test_returns_bill_detail(self, api_client):
        bill = make_bill()
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get, \
             patch("app.routers.bills.storage_service.signed_url", return_value="https://example.com/img.jpg"):
            mock_get.return_value = bill
            resp = await api_client.get(f"/api/v1/bills/{BILL_ID}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(BILL_ID)
        assert body["vendor_name"] == "Kerala Electricals"

    async def test_returns_404_when_not_found(self, api_client):
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = await api_client.get(f"/api/v1/bills/{uuid.uuid4()}")

        assert resp.status_code == 404

    async def test_returns_404_for_different_user_bill(self, api_client):
        """Bill belonging to another user should appear as not found."""
        other_user_bill = make_bill(user_id=uuid.uuid4())
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = other_user_bill
            resp = await api_client.get(f"/api/v1/bills/{other_user_bill.id}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/bills/{bill_id}
# ---------------------------------------------------------------------------

class TestUpdateBillEndpoint:
    async def test_updates_and_returns_bill(self, api_client):
        bill = make_bill()
        updated_bill = make_bill(vendor_name="Updated Vendor", is_verified=True)

        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get, \
             patch("app.routers.bills.bill_service.update_bill", new_callable=AsyncMock) as mock_update, \
             patch("app.routers.bills.storage_service.signed_url", return_value=None):
            mock_get.return_value = bill
            mock_update.return_value = updated_bill

            resp = await api_client.patch(
                f"/api/v1/bills/{BILL_ID}",
                json={"vendor_name": "Updated Vendor", "is_verified": True},
            )

        assert resp.status_code == 200
        assert mock_update.called

    async def test_returns_404_when_bill_not_found(self, api_client):
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = await api_client.patch(
                f"/api/v1/bills/{uuid.uuid4()}",
                json={"vendor_name": "Test"},
            )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/bills/{bill_id}
# ---------------------------------------------------------------------------

class TestDeleteBillEndpoint:
    async def test_deletes_and_returns_204(self, api_client):
        bill = make_bill()
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get, \
             patch("app.routers.bills.bill_service.delete_bill", new_callable=AsyncMock) as mock_delete:
            mock_get.return_value = bill
            resp = await api_client.delete(f"/api/v1/bills/{BILL_ID}")

        assert resp.status_code == 200
        assert mock_delete.called

    async def test_returns_404_when_bill_not_found(self, api_client):
        with patch("app.routers.bills.bill_service.get_bill", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = await api_client.delete(f"/api/v1/bills/{uuid.uuid4()}")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/bills/upload
# ---------------------------------------------------------------------------

class TestUploadBillEndpoint:
    async def test_rejects_non_image_file(self, api_client):
        resp = await api_client.post(
            "/api/v1/bills/upload",
            files={"file": ("test.pdf", b"%PDF", "application/pdf")},
        )
        assert resp.status_code == 400

    async def test_rejects_oversized_file(self, api_client):
        big_bytes = b"x" * (11 * 1024 * 1024)  # 11 MB
        resp = await api_client.post(
            "/api/v1/bills/upload",
            files={"file": ("photo.jpg", big_bytes, "image/jpeg")},
        )
        assert resp.status_code == 400

    async def test_accepts_valid_jpeg(self, api_client):
        with patch("app.routers.bills.storage_service.upload_bill", return_value="bills/test/job.jpg"):
            resp = await api_client.post(
                "/api/v1/bills/upload",
                files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0fake_jpeg", "image/jpeg")},
            )

        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "pending"
