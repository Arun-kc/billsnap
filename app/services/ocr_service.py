"""
OCR extraction service using Claude Vision.
Haiku handles most bills; Sonnet is the fallback for low-confidence results.
Prompt and logic adapted from evals/ocr_benchmark/benchmark.py.
"""

import base64
import json
import re
from dataclasses import dataclass, field

import anthropic

from ..config import settings

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# Haiku pricing: $0.80/M input, $4.00/M output
# Sonnet pricing: $3.00/M input, $15.00/M output
_MODEL_PRICING = {
    HAIKU_MODEL: (0.80, 4.00),
    SONNET_MODEL: (3.00, 15.00),
}

EXTRACTION_PROMPT = """You are extracting structured data from an Indian business document (tax invoice, credit note, delivery challan, or bill of supply).

STEP 1 — Identify the document type:
- "Tax Invoice" → type = "tax_invoice"
- "Credit Note" or "Debit Note" → type = "credit_note"
- "Delivery Challan" → type = "delivery_challan"
- "Bill of Supply" → type = "bill_of_supply"
If unclear, use "tax_invoice" as default.

STEP 2 — Read handwritten portions carefully:
Read digit-by-digit. Common confusion: 0 vs O, 1 vs I, 5 vs S, 8 vs B.

STEP 3 — Validate the GSTIN:
A valid GSTIN is exactly 15 characters: [2-digit state code][10-char PAN][1 entity number][Z][1 check digit].
State code 32 = Kerala. 33 = Tamil Nadu. 27 = Maharashtra.

STEP 4 — Extract fields.

For tax_invoice / bill_of_supply / delivery_challan:
{
  "document_type": "tax_invoice",
  "vendor_name": "Seller name",
  "vendor_gstin": "Seller GSTIN (exactly 15 chars)",
  "buyer_name": "Buyer name if present",
  "buyer_gstin": "Buyer GSTIN if present",
  "bill_number": "Invoice number",
  "bill_date": "YYYY-MM-DD",
  "total_amount": 1234.56,
  "taxable_amount": 1000.00,
  "cgst_amount": 90.00,
  "sgst_amount": 90.00,
  "igst_amount": null,
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "line_items": [
    { "description": "Item", "hsn_code": "1234", "quantity": 2, "unit": "pcs", "unit_price": 500.00, "amount": 1000.00 }
  ],
  "field_confidence": { "vendor_gstin": "high", "total_amount": "high", "tax_amounts": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear or handwritten"
}

For credit_note / debit_note:
{
  "document_type": "credit_note",
  "vendor_name": "Issuer name",
  "vendor_gstin": "Issuer GSTIN (exactly 15 chars)",
  "document_number": "Credit note number",
  "document_date": "YYYY-MM-DD",
  "original_invoice_number": "Invoice this note is against",
  "original_invoice_date": "YYYY-MM-DD if shown",
  "credit_amount": 500.00,
  "cgst_amount": null,
  "sgst_amount": null,
  "igst_amount": null,
  "reason": "Reason if stated",
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "field_confidence": { "vendor_gstin": "high", "credit_amount": "high", "original_invoice_number": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear"
}

Return ONLY the JSON object, no explanation."""


@dataclass
class ExtractionResult:
    extracted: dict
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_inr: float
    confidence: str = "high"
    needs_review: bool = False


def _is_valid_gstin(gstin: str | None) -> bool:
    if not gstin or gstin in ("null", ""):
        return False
    return bool(re.fullmatch(r"[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", gstin))


def _cost_inr(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _MODEL_PRICING.get(model, (3.00, 15.00))
    cost_usd = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return round(cost_usd * 84, 4)


def _needs_sonnet_retry(extracted: dict, confidence_threshold: float) -> bool:
    confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
    confidence_str = extracted.get("extraction_confidence", "high")
    confidence = confidence_map.get(confidence_str, 1.0)
    if confidence < confidence_threshold:
        return True
    if confidence_str == "medium":
        gstin_invalid = not _is_valid_gstin(extracted.get("vendor_gstin"))
        tax_missing = all(
            extracted.get(k) in (None, "null", "")
            for k in ("cgst_amount", "sgst_amount", "igst_amount")
        )
        return gstin_invalid or tax_missing
    return False


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_parse_error": raw, "extraction_confidence": "low"}


async def _call_claude(image_bytes: bytes, content_type: str, model: str) -> tuple[dict, int, int]:
    """Call Claude vision and return (extracted_dict, input_tokens, output_tokens)."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Map content type to Anthropic media type
    media_type_map = {
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/webp": "image/webp",
    }
    media_type = media_type_map.get(content_type, "image/jpeg")

    message = client.messages.create(
        model=model,
        max_tokens=1536,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_data},
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    extracted = _parse_json_response(message.content[0].text)
    return extracted, message.usage.input_tokens, message.usage.output_tokens


async def extract(image_bytes: bytes, content_type: str) -> ExtractionResult:
    """
    Extract GST fields from a bill image.
    Starts with Haiku; automatically retries with Sonnet if confidence is low
    or critical fields (GSTIN, tax amounts) are suspect.
    """
    threshold = settings.ocr_confidence_threshold

    # First pass — Haiku
    extracted, in_tok, out_tok = await _call_claude(image_bytes, content_type, HAIKU_MODEL)
    model_used = HAIKU_MODEL
    total_in, total_out = in_tok, out_tok

    # Sonnet fallback
    if _needs_sonnet_retry(extracted, threshold):
        extracted2, in_tok2, out_tok2 = await _call_claude(image_bytes, content_type, SONNET_MODEL)
        conf2 = extracted2.get("extraction_confidence", "low")
        conf1 = extracted.get("extraction_confidence", "low")
        # Use Sonnet result if it's equal or better confidence
        conf_rank = {"high": 2, "medium": 1, "low": 0}
        if conf_rank.get(conf2, 0) >= conf_rank.get(conf1, 0) or not extracted.get("vendor_name"):
            extracted = extracted2
            model_used = SONNET_MODEL
        total_in += in_tok2
        total_out += out_tok2

    confidence = extracted.get("extraction_confidence", "low")
    cost_inr = _cost_inr(HAIKU_MODEL, in_tok, out_tok)
    if model_used == SONNET_MODEL:
        cost_inr += _cost_inr(SONNET_MODEL, in_tok2, out_tok2)

    return ExtractionResult(
        extracted=extracted,
        model_used=model_used,
        input_tokens=total_in,
        output_tokens=total_out,
        cost_inr=cost_inr,
        confidence=confidence,
        needs_review=(confidence == "low"),
    )
