"""
Unit tests for app.services.ocr_service.

All tests operate on pure/sync functions. The async extract() function
is tested by mocking _call_claude to avoid real API calls.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ocr_service import (
    HAIKU_MODEL,
    SONNET_MODEL,
    ExtractionResult,
    _cost_inr,
    _is_valid_gstin,
    _needs_sonnet_retry,
    _parse_json_response,
    extract,
)


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_clean_json(self):
        raw = '{"vendor_name": "Test", "total_amount": 100}'
        result = _parse_json_response(raw)
        assert result["vendor_name"] == "Test"
        assert result["total_amount"] == 100

    def test_fenced_json_backticks(self):
        raw = "```json\n{\"vendor_name\": \"Test\"}\n```"
        result = _parse_json_response(raw)
        assert result["vendor_name"] == "Test"

    def test_fenced_without_language(self):
        raw = "```\n{\"total_amount\": 500}\n```"
        result = _parse_json_response(raw)
        assert result["total_amount"] == 500

    def test_invalid_json_returns_parse_error(self):
        raw = "not json at all"
        result = _parse_json_response(raw)
        assert "_parse_error" in result
        assert result["extraction_confidence"] == "low"

    def test_leading_whitespace_stripped(self):
        raw = "   {\"bill_number\": \"INV-1\"}   "
        result = _parse_json_response(raw)
        assert result["bill_number"] == "INV-1"


# ---------------------------------------------------------------------------
# _is_valid_gstin
# ---------------------------------------------------------------------------

class TestIsValidGstin:
    def test_valid_kerala_gstin(self):
        assert _is_valid_gstin("32ABCDE1234F1Z5") is True

    def test_valid_maharashtra_gstin(self):
        assert _is_valid_gstin("27XXXXX1234X1ZX") is True

    def test_none_is_invalid(self):
        assert _is_valid_gstin(None) is False

    def test_empty_string_is_invalid(self):
        assert _is_valid_gstin("") is False

    def test_null_string_is_invalid(self):
        assert _is_valid_gstin("null") is False

    def test_too_short_is_invalid(self):
        assert _is_valid_gstin("32ABCDE1234F1Z") is False

    def test_too_long_is_invalid(self):
        assert _is_valid_gstin("32ABCDE1234F1Z56") is False

    def test_invalid_state_code_is_invalid(self):
        # State code > 37 is invalid (35 Andaman & Nicobar, 36 Telangana, 37 Andhra Pradesh)
        assert _is_valid_gstin("99ABCDE1234F1Z5") is False


# ---------------------------------------------------------------------------
# _needs_sonnet_retry
# ---------------------------------------------------------------------------

class TestNeedsSonnetRetry:
    def test_low_confidence_triggers_retry(self):
        extracted = {"extraction_confidence": "low", "vendor_name": "Test"}
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.70) is True

    def test_high_confidence_no_retry(self):
        extracted = {
            "extraction_confidence": "high",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "cgst_amount": 90.0,
        }
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.70) is False

    def test_medium_with_invalid_gstin_triggers_retry(self):
        # threshold=0.50: medium (0.6) passes confidence check; invalid GSTIN triggers retry
        extracted = {
            "extraction_confidence": "medium",
            "vendor_gstin": "INVALID",
            "cgst_amount": 90.0,
        }
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.50) is True

    def test_medium_with_missing_tax_triggers_retry(self):
        # threshold=0.50: medium (0.6) passes confidence check; missing tax triggers retry
        extracted = {
            "extraction_confidence": "medium",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "cgst_amount": None,
            "sgst_amount": None,
            "igst_amount": None,
        }
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.50) is True

    def test_medium_with_valid_fields_no_retry(self):
        # threshold=0.50: medium (0.6) passes; valid GSTIN + tax present → no retry
        extracted = {
            "extraction_confidence": "medium",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
        }
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.50) is False

    def test_threshold_boundary(self):
        # confidence=0.6 (medium) < confidence_threshold=0.70 → retry
        extracted = {"extraction_confidence": "medium"}
        assert _needs_sonnet_retry(extracted, confidence_threshold=0.70) is True


# ---------------------------------------------------------------------------
# _cost_inr
# ---------------------------------------------------------------------------

class TestCostInr:
    def test_haiku_cost_calculation(self):
        # 1000 input tokens at $0.80/M + 200 output tokens at $4.00/M
        # cost_usd = (1000 * 0.80 + 200 * 4.00) / 1_000_000 = 0.00000080 + 0.00000080 = 0.0000016
        # cost_inr = 0.0000016 * 84 = 0.000134... rounds to 4 dp
        cost = _cost_inr(HAIKU_MODEL, 1000, 200)
        assert cost > 0
        assert isinstance(cost, float)

    def test_sonnet_costs_more_than_haiku(self):
        cost_haiku = _cost_inr(HAIKU_MODEL, 1000, 200)
        cost_sonnet = _cost_inr(SONNET_MODEL, 1000, 200)
        assert cost_sonnet > cost_haiku

    def test_zero_tokens_returns_zero(self):
        assert _cost_inr(HAIKU_MODEL, 0, 0) == 0.0


# ---------------------------------------------------------------------------
# extract (async, mocked)
# ---------------------------------------------------------------------------

class TestExtract:
    @pytest.fixture
    def haiku_result(self):
        return {
            "document_type": "tax_invoice",
            "vendor_name": "Kerala Electricals",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "bill_date": "2026-04-10",
            "total_amount": 1180.0,
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
            "extraction_confidence": "high",
        }

    async def test_high_confidence_uses_haiku_only(self, haiku_result):
        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (haiku_result, 500, 200)

            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert mock_call.call_count == 1  # Haiku only, no Sonnet retry
        assert result.model_used == HAIKU_MODEL
        assert result.confidence == "high"
        assert result.needs_review is False

    async def test_low_confidence_triggers_sonnet_retry(self):
        haiku_result = {
            "extraction_confidence": "low",
            "vendor_name": "Blurry Vendor",
        }
        sonnet_result = {
            "extraction_confidence": "high",
            "vendor_name": "Clear Vendor",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "cgst_amount": 90.0,
            "sgst_amount": 90.0,
        }

        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [(haiku_result, 500, 100), (sonnet_result, 600, 150)]

            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert mock_call.call_count == 2
        assert result.model_used == SONNET_MODEL
        assert result.confidence == "high"

    async def test_low_confidence_result_sets_needs_review(self):
        low_result = {
            "extraction_confidence": "low",
            "vendor_name": None,
        }

        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            # Both Haiku and Sonnet return low confidence
            mock_call.side_effect = [(low_result, 400, 100), (low_result, 500, 120)]

            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert result.needs_review is True

    async def test_extraction_result_includes_cost(self, haiku_result):
        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (haiku_result, 1000, 300)

            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert result.cost_inr > 0
        assert result.input_tokens == 1000
        assert result.output_tokens == 300
