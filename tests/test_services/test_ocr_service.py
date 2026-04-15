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
    _is_ocr_blank,
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
    """The retry gate is structural: self-reported confidence no longer matters.

    We retry only when a required field is broken — missing vendor, missing
    amount, invalid GSTIN regex, or a word-form/numeric disagreement.
    """

    def test_missing_vendor_name_triggers_retry(self):
        extracted = {"vendor_name": None, "total_amount": 1000.0}
        assert _needs_sonnet_retry(extracted) is True

    def test_short_vendor_name_triggers_retry(self):
        extracted = {"vendor_name": "XY", "total_amount": 1000.0}
        assert _needs_sonnet_retry(extracted) is True

    def test_missing_total_amount_triggers_retry(self):
        extracted = {"vendor_name": "Kerala Electricals", "total_amount": None}
        assert _needs_sonnet_retry(extracted) is True

    def test_invalid_vendor_gstin_triggers_retry(self):
        extracted = {
            "vendor_name": "Kerala Electricals",
            "total_amount": 1180.0,
            "vendor_gstin": "NOT-A-GSTIN",
        }
        assert _needs_sonnet_retry(extracted) is True

    def test_medium_confidence_alone_does_not_trigger_retry(self):
        extracted = {
            "extraction_confidence": "medium",
            "vendor_name": "Kerala Electricals",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "total_amount": 1180.0,
        }
        assert _needs_sonnet_retry(extracted) is False

    def test_complete_high_confidence_no_retry(self):
        extracted = {
            "extraction_confidence": "high",
            "vendor_name": "Kerala Electricals",
            "vendor_gstin": "32ABCDE1234F1Z5",
            "total_amount": 1180.0,
            "cgst_amount": 90.0,
        }
        assert _needs_sonnet_retry(extracted) is False

    def test_credit_note_uses_credit_amount(self):
        extracted = {
            "document_type": "credit_note",
            "vendor_name": "Thanks Marketing",
            "credit_amount": 4344.0,
        }
        assert _needs_sonnet_retry(extracted) is False

    def test_credit_note_missing_credit_amount_triggers_retry(self):
        extracted = {
            "document_type": "credit_note",
            "vendor_name": "Thanks Marketing",
            "credit_amount": None,
        }
        assert _needs_sonnet_retry(extracted) is True

    def test_word_form_mismatch_triggers_retry(self):
        extracted = {
            "vendor_name": "Kerala Electricals",
            "total_amount": 10200000.0,
            "total_amount_in_words": "Rupees Ten Thousand Two Hundred Only",
        }
        assert _needs_sonnet_retry(extracted) is True


# ---------------------------------------------------------------------------
# _is_ocr_blank
# ---------------------------------------------------------------------------


class TestIsOcrBlank:
    def test_all_critical_fields_null_is_blank(self):
        extracted = {"document_type": "tax_invoice", "vendor_name": None, "total_amount": None, "bill_date": None}
        assert _is_ocr_blank(extracted) is True

    def test_one_critical_field_populated_is_not_blank(self):
        extracted = {"document_type": "tax_invoice", "vendor_name": "KS Traders", "total_amount": None, "bill_date": None}
        assert _is_ocr_blank(extracted) is False

    def test_credit_note_uses_credit_fields(self):
        extracted = {"document_type": "credit_note", "vendor_name": None, "credit_amount": None, "document_date": None}
        assert _is_ocr_blank(extracted) is True

    def test_credit_note_with_amount_is_not_blank(self):
        extracted = {"document_type": "credit_note", "vendor_name": None, "credit_amount": 500.0, "document_date": None}
        assert _is_ocr_blank(extracted) is False

    def test_empty_string_treated_as_blank(self):
        extracted = {"document_type": "tax_invoice", "vendor_name": "", "total_amount": "null", "bill_date": ""}
        assert _is_ocr_blank(extracted) is True


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

    async def test_all_null_result_sets_needs_manual_entry(self):
        """Illegible handwritten bills (e.g. billsample3): both models return blank."""
        blank = {
            "document_type": "tax_invoice",
            "vendor_name": None,
            "total_amount": None,
            "bill_date": None,
        }
        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [(blank, 300, 50), (blank, 400, 60)]
            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert result.needs_manual_entry is True
        assert result.needs_review is True
        assert "MANUAL_ENTRY_REQUIRED" in result.extracted.get("extraction_notes", "")

    async def test_populated_result_does_not_set_needs_manual_entry(self, haiku_result):
        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (haiku_result, 500, 200)
            result = await extract(b"fake_image_bytes", "image/jpeg")
        assert result.needs_manual_entry is False

    async def test_extraction_result_includes_cost(self, haiku_result):
        with patch("app.services.ocr_service._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = (haiku_result, 1000, 300)

            result = await extract(b"fake_image_bytes", "image/jpeg")

        assert result.cost_inr > 0
        assert result.input_tokens == 1000
        assert result.output_tokens == 300
