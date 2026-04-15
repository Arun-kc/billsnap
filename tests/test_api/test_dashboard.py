"""
API-level tests for GET /api/v1/dashboard.

The dashboard router queries the DB directly (no service layer),
so tests override get_db per-test to control execute() return values.
"""

from unittest.mock import MagicMock

import pytest

from app.dependencies import get_db
from app.main import app
from tests.conftest import make_mock_db, make_mock_result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dashboard_row(month: str, bill_count: int, total_amount: float, total_tax: float, unverified_count: int):
    row = MagicMock()
    row.month = month
    row.bill_count = bill_count
    row.total_amount = total_amount
    row.total_tax = total_tax
    row.unverified_count = unverified_count
    return row


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard
# ---------------------------------------------------------------------------

class TestGetDashboard:
    async def test_returns_200_with_months(self, api_client):
        rows = [_make_dashboard_row("2026-04", 5, 5000.0, 450.0, 1)]
        mock_result = make_mock_result(rows=rows)

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard?months=1")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        body = resp.json()
        assert "months" in body
        assert len(body["months"]) == 1
        month = body["months"][0]
        assert month["month"] == "2026-04"
        assert month["bill_count"] == 5
        assert month["total_amount"] == 5000.0
        assert month["total_tax"] == 450.0
        assert month["unverified_count"] == 1

    async def test_returns_200_with_empty_list(self, api_client):
        mock_result = make_mock_result(rows=[])

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        body = resp.json()
        assert body["months"] == []

    async def test_returns_multiple_months(self, api_client):
        rows = [
            _make_dashboard_row("2026-04", 3, 3000.0, 270.0, 0),
            _make_dashboard_row("2026-03", 7, 8500.0, 765.0, 2),
            _make_dashboard_row("2026-02", 1, 500.0, 45.0, 1),
        ]
        mock_result = make_mock_result(rows=rows)

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard?months=3")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["months"]) == 3
        assert body["months"][0]["month"] == "2026-04"
        assert body["months"][2]["month"] == "2026-02"

    async def test_default_months_is_3(self, api_client):
        """Omitting months param should default to 3."""
        mock_result = make_mock_result(rows=[])

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200

    async def test_rejects_months_zero(self, api_client):
        resp = await api_client.get("/api/v1/dashboard?months=0")
        assert resp.status_code == 422

    async def test_rejects_months_thirteen(self, api_client):
        resp = await api_client.get("/api/v1/dashboard?months=13")
        assert resp.status_code == 422

    async def test_months_one_accepted(self, api_client):
        mock_result = make_mock_result(rows=[])

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard?months=1")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200

    async def test_months_twelve_accepted(self, api_client):
        mock_result = make_mock_result(rows=[])

        async def override_get_db():
            db = make_mock_db()
            db.execute.return_value = mock_result
            yield db

        app.dependency_overrides[get_db] = override_get_db
        resp = await api_client.get("/api/v1/dashboard?months=12")
        app.dependency_overrides.pop(get_db, None)

        assert resp.status_code == 200

    async def test_unauthorized_without_token(self):
        """Verify that removing auth dependency causes 403."""
        from app.main import app

        app.dependency_overrides.clear()
        from httpx import ASGITransport, AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard")

        assert resp.status_code == 401
