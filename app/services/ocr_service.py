"""
OCR extraction service using Claude Vision.
Haiku handles most bills; Sonnet is the fallback for low-confidence results.
Prompt and logic adapted from evals/ocr_benchmark/benchmark.py.
"""

import base64
import io
import json
import re
from dataclasses import dataclass

import anthropic
from PIL import Image, ExifTags

from ..config import settings

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

# Haiku pricing: $0.80/M input, $4.00/M output
# Sonnet pricing: $3.00/M input, $15.00/M output
_MODEL_PRICING = {
    HAIKU_MODEL: (0.80, 4.00),
    SONNET_MODEL: (3.00, 15.00),
}

# Module-level async client (reuses HTTP connection)
_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

EXTRACTION_PROMPT = """You are extracting structured data from an Indian business document photo.

STEP 1 — Identify the document type:
- "Tax Invoice" → "tax_invoice"
- "Credit Note" / "Debit Note" → "credit_note" / "debit_note"
- "Delivery Challan" → "delivery_challan"
- "Bill of Supply" → "bill_of_supply"
- Plain receipt → "receipt"
Default: "tax_invoice"

STEP 2 — Find the VENDOR NAME (seller/supplier):
Look at the TOP of the document — the business name is usually the largest text in the header or printed on the letterhead. It is NOT the buyer name. Common patterns: "M/s. XYZ Traders", "ABC Enterprises", "Sri Ganesh Stores".

STEP 3 — Read amounts carefully:
- Indian format uses commas as thousands separators: ₹1,23,456.78 = 123456.78
- The TOTAL AMOUNT is the final payable amount (after tax), often labeled "Total", "Grand Total", "Net Payable", "Amount Payable"
- TAXABLE AMOUNT is the pre-tax subtotal
- CGST + SGST are each half the GST; IGST replaces both for inter-state

STEP 4 — Read handwritten portions digit-by-digit:
Common confusion: 0↔O, 1↔I, 5↔S, 8↔B, 6↔G

STEP 5 — Validate the GSTIN (exactly 15 chars):
Pattern: [2-digit state][10-char PAN][entity digit][Z][check digit]
Kerala=32, Tamil Nadu=33, Maharashtra=27, Karnataka=29, Delhi=07

STEP 6 — Return JSON ONLY (no markdown, no explanation):

For tax_invoice / bill_of_supply / receipt / delivery_challan:
{
  "document_type": "tax_invoice",
  "vendor_name": "Exact seller business name from header",
  "vendor_gstin": "15-char GSTIN or null",
  "buyer_name": "Buyer name if shown or null",
  "buyer_gstin": "Buyer GSTIN if shown or null",
  "bill_number": "Invoice/receipt number or null",
  "bill_date": "YYYY-MM-DD or null",
  "total_amount": 1234.56,
  "taxable_amount": 1000.00,
  "cgst_amount": 90.00,
  "sgst_amount": 90.00,
  "igst_amount": null,
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "line_items": [
    { "description": "Item name", "hsn_code": "1234", "quantity": 2.0, "unit": "pcs", "unit_price": 500.00, "amount": 1000.00 }
  ],
  "field_confidence": { "vendor_name": "high", "vendor_gstin": "high", "total_amount": "high", "bill_date": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear, handwritten, or missing"
}

For credit_note / debit_note:
{
  "document_type": "credit_note",
  "vendor_name": "Issuer business name",
  "vendor_gstin": "Issuer GSTIN or null",
  "document_number": "Credit/debit note number",
  "document_date": "YYYY-MM-DD or null",
  "original_invoice_number": "Invoice reference or null",
  "original_invoice_date": "YYYY-MM-DD or null",
  "credit_amount": 500.00,
  "cgst_amount": null,
  "sgst_amount": null,
  "igst_amount": null,
  "reason": "Reason if stated or null",
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "field_confidence": { "vendor_name": "high", "credit_amount": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear"
}

Rules:
- Use null (not "null" string) for missing fields
- Amounts must be numbers, never strings
- extraction_confidence = "low" if vendor_name or total_amount is missing/unclear"""


@dataclass
class ExtractionResult:
    extracted: dict
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_inr: float
    confidence: str = "high"
    needs_review: bool = False


def _fix_orientation(image_bytes: bytes) -> bytes:
    """
    Auto-rotate image based on EXIF orientation tag.
    Mobile photos often arrive with EXIF rotation; Claude sees them sideways
    which hurts OCR accuracy significantly.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))

        # Find the EXIF orientation tag number
        orientation_tag = None
        for tag, name in ExifTags.TAGS.items():
            if name == "Orientation":
                orientation_tag = tag
                break

        if orientation_tag is None:
            return image_bytes

        exif = img._getexif()  # type: ignore[attr-defined]
        if not exif or orientation_tag not in exif:
            return image_bytes

        orientation = exif[orientation_tag]
        rotation_map = {
            3: Image.ROTATE_180,
            6: Image.ROTATE_270,
            8: Image.ROTATE_90,
        }
        if orientation in rotation_map:
            img = img.transpose(rotation_map[orientation])

        buf = io.BytesIO()
        # Preserve format; default to JPEG if unknown
        fmt = img.format or "JPEG"
        if fmt == "MPO":
            fmt = "JPEG"
        img.save(buf, format=fmt, quality=90)
        return buf.getvalue()

    except Exception:
        # If anything goes wrong, return original bytes unchanged
        return image_bytes


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
    # Always retry if vendor name is missing or suspicious
    vendor = extracted.get("vendor_name") or ""
    if not vendor or len(vendor) < 3 or vendor.lower() in ("unknown", "null", "n/a"):
        return True
    # Retry if GSTIN looks invalid and tax amounts are missing
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
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    media_type_map = {
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/webp": "image/webp",
    }
    media_type = media_type_map.get(content_type, "image/jpeg")

    message = await _client.messages.create(
        model=model,
        max_tokens=2048,
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
    1. Fixes EXIF orientation so mobile photos are right-side up.
    2. Tries Haiku first for cost efficiency.
    3. Retries with Sonnet if confidence is low or key fields are missing.
    """
    # Fix mobile photo orientation before sending to Claude
    image_bytes = _fix_orientation(image_bytes)

    threshold = settings.ocr_confidence_threshold

    # First pass — Haiku
    extracted, in_tok, out_tok = await _call_claude(image_bytes, content_type, HAIKU_MODEL)
    model_used = HAIKU_MODEL
    in_tok2, out_tok2 = 0, 0

    # Sonnet fallback
    if _needs_sonnet_retry(extracted, threshold):
        extracted2, in_tok2, out_tok2 = await _call_claude(image_bytes, content_type, SONNET_MODEL)
        conf2 = extracted2.get("extraction_confidence", "low")
        conf1 = extracted.get("extraction_confidence", "low")
        conf_rank = {"high": 2, "medium": 1, "low": 0}
        # Use Sonnet result if it's at least as confident, or if Haiku had no vendor name
        if conf_rank.get(conf2, 0) >= conf_rank.get(conf1, 0) or not extracted.get("vendor_name"):
            extracted = extracted2
            model_used = SONNET_MODEL

    confidence = extracted.get("extraction_confidence", "low")
    cost_inr = _cost_inr(HAIKU_MODEL, in_tok, out_tok)
    if model_used == SONNET_MODEL:
        cost_inr += _cost_inr(SONNET_MODEL, in_tok2, out_tok2)

    # Flag for review if medium or low confidence, or if critical fields are empty
    vendor_ok = bool(extracted.get("vendor_name") and len(extracted.get("vendor_name", "")) >= 3)
    amount_ok = extracted.get("total_amount") not in (None, "null", "")
    needs_review = confidence in ("low", "medium") or not vendor_ok or not amount_ok

    return ExtractionResult(
        extracted=extracted,
        model_used=model_used,
        input_tokens=in_tok + in_tok2,
        output_tokens=out_tok + out_tok2,
        cost_inr=cost_inr,
        confidence=confidence,
        needs_review=needs_review,
    )
