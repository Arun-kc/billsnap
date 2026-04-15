"""
Unit tests for app.workers.ocr_worker.

_reset_stuck_jobs and _process_job are tested with mocked db and services.
run_worker is tested for its startup behavior only (not the infinite loop).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.ocr_worker import _process_job, _reset_stuck_jobs
from tests.conftest import JOB_ID, USER_ID, make_mock_db, make_ocr_job


# ---------------------------------------------------------------------------
# _reset_stuck_jobs
# ---------------------------------------------------------------------------

class TestResetStuckJobs:
    async def test_executes_update_and_commits(self):
        db = make_mock_db()
        await _reset_stuck_jobs(db)

        assert db.execute.called
        assert db.commit.called

    async def test_calls_execute_once(self):
        db = make_mock_db()
        await _reset_stuck_jobs(db)

        assert db.execute.call_count == 1


# ---------------------------------------------------------------------------
# _process_job
# ---------------------------------------------------------------------------

class TestProcessJob:
    @pytest.fixture
    def high_confidence_result(self):
        result = MagicMock()
        result.extracted = {
            "document_type": "tax_invoice",
            "vendor_name": "Kerala Electricals",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "bill_date": "2026-04-10",
            "total_amount": 1180.0,
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
            "extraction_notes": None,
        }
        result.confidence = "high"
        result.needs_review = False
        result.needs_manual_entry = False
        result.model_used = "claude-haiku-4-5-20251001"
        result.cost_inr = 0.05
        result.input_tokens = 1000
        result.output_tokens = 300
        return result

    async def test_marks_job_completed_on_success(self, high_confidence_result):
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = high_confidence_result
            await _process_job(job, db)

        assert job.status == "completed"

    async def test_marks_job_needs_review_when_low_confidence(self):
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        result = MagicMock()
        result.extracted = {"vendor_name": None}
        result.confidence = "low"
        result.needs_review = True
        result.needs_manual_entry = False
        result.model_used = "claude-haiku-4-5-20251001"
        result.cost_inr = 0.03
        result.input_tokens = 800
        result.output_tokens = 100

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = result
            await _process_job(job, db)

        assert job.status == "needs_review"

    async def test_marks_job_needs_manual_entry_when_ocr_blank(self):
        """Illegible bill: ocr_service flags needs_manual_entry, worker records status."""
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        result = MagicMock()
        result.extracted = {"vendor_name": None, "total_amount": None, "bill_date": None}
        result.confidence = "low"
        result.needs_review = True
        result.needs_manual_entry = True
        result.model_used = "claude-sonnet-4-6"
        result.cost_inr = 2.10
        result.input_tokens = 900
        result.output_tokens = 60

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = result
            await _process_job(job, db)

        assert job.status == "needs_manual_entry"

    async def test_marks_job_failed_on_exception(self):
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        with patch("app.workers.ocr_worker.storage_service.download", side_effect=Exception("S3 down")):
            await _process_job(job, db)

        assert job.status == "failed"
        assert "S3 down" in job.error_message

    async def test_commits_twice_on_success(self, high_confidence_result):
        """First commit marks processing; second commit marks completed."""
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = high_confidence_result
            await _process_job(job, db)

        assert db.commit.call_count == 2

    async def test_sets_started_at_before_processing(self, high_confidence_result):
        db = make_mock_db()
        job = make_ocr_job(status="pending")
        assert job.started_at is None

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = high_confidence_result
            await _process_job(job, db)

        assert job.started_at is not None

    async def test_thumbnail_failure_does_not_fail_job(self, high_confidence_result):
        """Thumbnail errors are caught and logged; job should still complete."""
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", side_effect=Exception("thumb fail")), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = high_confidence_result
            await _process_job(job, db)

        assert job.status == "completed"

    async def test_model_tier_set_to_haiku(self, high_confidence_result):
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = high_confidence_result
            await _process_job(job, db)

        assert job.model_tier == "haiku"

    async def test_model_tier_set_to_sonnet(self):
        db = make_mock_db()
        job = make_ocr_job(status="pending")

        result = MagicMock()
        result.extracted = {"vendor_name": "Test"}
        result.confidence = "high"
        result.needs_review = False
        result.model_used = "claude-sonnet-4-6"
        result.cost_inr = 0.50
        result.input_tokens = 2000
        result.output_tokens = 500

        with patch("app.workers.ocr_worker.storage_service.download", return_value=b"fake_bytes"), \
             patch("app.workers.ocr_worker.storage_service.upload_thumbnail", return_value="thumbs/t.jpg"), \
             patch("app.workers.ocr_worker.ocr_service.extract", new_callable=AsyncMock) as mock_extract, \
             patch("app.workers.ocr_worker.bill_service.create_from_ocr", new_callable=AsyncMock):
            mock_extract.return_value = result
            await _process_job(job, db)

        assert job.model_tier == "sonnet"
