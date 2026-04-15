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

The photo was taken by a non-technical user on a smartphone and may be blurry, shaky, or low-light.
Use every available inference strategy rather than giving up:
- If a character is unclear, infer from context (₹X,XXX.XX price formats, GSTIN structure, column alignment)
- Only return null for a field if it is truly absent from the document — prefer a best-guess with low confidence over null

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
- PRESERVE ALL DECIMAL DIGITS (paise). ₹1,234.50 → 1234.50 (never 1234). ₹850.00 → 850.00.
- TOTAL AMOUNT = the FINAL payable figure after ALL taxes are added.
  Look for these labels (in priority order): "Grand Total", "Invoice Total", "Total Amount", "Net Payable", "Amount Payable", "Net Amount", "Amount Due", "Balance Due", "Total"
  If multiple "Total" rows exist, use the LAST / LARGEST one that includes all taxes.
  Never use a subtotal or taxable amount as the total.
- TAXABLE AMOUNT is the pre-tax subtotal (before CGST/SGST/IGST)
- CGST + SGST are each half the GST; IGST replaces both for inter-state
- SYMMETRY CHECK: For intra-state invoices, CGST always equals SGST exactly. Use one to verify or infer the other if one is unclear.
- MATH VERIFICATION: taxable_amount + cgst_amount + sgst_amount + igst_amount should equal total_amount. Use this identity to infer a missing value when others are visible.
- TAX SLAB: identify the GST rate applied — typically 5, 12, 18, or 28. Return "Mixed" if multiple rates appear on the same invoice. Return null if not determinable.

STEP 3.5 — WORD-FORM CROSS-CHECK (CRITICAL — prevents decimal/scale errors):
Indian tax invoices ALWAYS print the total amount spelled out in words, usually below the numeric total.
Common patterns: "Rupees Ten Thousand Two Hundred Only", "INR Four Thousand Nine Hundred Forty Four Only", "Amount in words: ...".
The word form is the AUTHORITATIVE ground truth for magnitude because:
- Words never have comma/period ambiguity (unlike "10,200.00" which can be misread at wrong scale)
- Words are written once carefully; numeric columns may have visually confusing formatting (e.g. 3-decimal line items)

MANDATORY procedure:
1. Locate and read the amount-in-words phrase. Transcribe it verbatim into total_amount_in_words.
2. Mentally parse the words to a number. Example: "Ten Thousand Two Hundred" = 10200.
3. Compare to your numeric total_amount. If they disagree in magnitude (off by 10×, 100×, 1000×), the WORD form WINS — overwrite total_amount to match the words, and note this in extraction_notes.
4. If the words say "Ten Thousand Two Hundred" but your numeric reading gave 10,200,000 — that's a 1000× scale error. Correct to 10200.00.
5. Only keep the numeric reading if it agrees with the words (allowing for rounding/round-off of a few rupees).
6. If no word-form is present, leave total_amount_in_words as null and rely on numeric reading alone.

STEP 4 — Read handwritten portions digit-by-digit:
Common confusion: 0↔O, 1↔I, 5↔S, 8↔B, 6↔G
For amounts: read each digit individually, then reconstruct the number.

STEP 5 — Identify GSTINs:
Bills often show TWO GSTINs — always assign them to the correct party:
- vendor_gstin = SELLER's GSTIN — the business that ISSUED this bill. Its name appears at the TOP/header of the document (letterhead). Usually labeled "GSTIN", "GST No", "Supplier GSTIN".
- buyer_gstin = BUYER's GSTIN — the business that RECEIVED this bill. Usually labeled "Bill To", "Buyer", "Consignee", "Customer GSTIN", "Recipient GSTIN".
- These are ALWAYS different values. Never put the buyer GSTIN in vendor_gstin.
- Validate each: exactly 15 chars, pattern [2-digit state][10-char PAN][entity digit][Z][check digit]
- State codes: Kerala=32, Tamil Nadu=33, Maharashtra=27, Karnataka=29, Delhi=07

STEP 6 — Return JSON ONLY (no markdown, no explanation):

For tax_invoice / bill_of_supply / receipt / delivery_challan:
{
  "document_type": "tax_invoice",
  "vendor_name": "Exact seller business name from header",
  "vendor_gstin": "Seller's 15-char GSTIN or null",
  "buyer_name": "Buyer name if shown or null",
  "buyer_gstin": "Buyer's 15-char GSTIN or null",
  "bill_number": "Invoice/receipt number or null",
  "bill_date": "YYYY-MM-DD or null",
  "total_amount": 1234.56,
  "total_amount_in_words": "Rupees One Thousand Two Hundred Thirty Four and Fifty Six Paise Only, or null if not shown",
  "taxable_amount": 1000.00,
  "cgst_amount": 90.00,
  "sgst_amount": 90.00,
  "igst_amount": null,
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "tax_slab": "5 | 12 | 18 | 28 | Mixed | null",
  "line_items": [
    { "description": "Item name", "hsn_code": "1234", "quantity": 2.0, "unit": "pcs", "unit_price": 500.00, "amount": 1000.00 }
  ],
  "field_confidence": { "vendor_name": "high", "vendor_gstin": "high", "total_amount": "high", "bill_date": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear, handwritten, or missing",
  "raw_text": "All visible text from the document in reading order"
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
  "credit_amount_in_words": "Rupees Five Hundred Only, or null if not shown",
  "cgst_amount": null,
  "sgst_amount": null,
  "igst_amount": null,
  "reason": "Reason if stated or null",
  "category": "electrical | materials | groceries | services | utilities | medical | transport | other",
  "field_confidence": { "vendor_name": "high", "credit_amount": "high" },
  "extraction_confidence": "high | medium | low",
  "extraction_notes": "Note anything unclear",
  "raw_text": "All visible text from the document in reading order"
}

Rules:
- Use null (not "null" string) for missing fields
- Amounts must be numbers, never strings
- NEVER round amounts — preserve exact paise (decimal places) as printed
- extraction_confidence = "low" if vendor_name or total_amount is missing/unclear
- Prefer a best-guess value (with low field_confidence) over null — only use null when the field is genuinely absent
- raw_text must include all text visible in the image, in reading order (top to bottom, left to right)"""


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


_WORD_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "lac": 100_000, "crore": 10_000_000, "million": 1_000_000, "billion": 1_000_000_000}


def _parse_amount_in_words(phrase: str | None) -> float | None:
    """Parse an Indian English amount phrase (e.g. 'Rupees Ten Thousand Two Hundred Only') to a number.

    Handles lakhs/crores and paise fractions. Returns None if unparseable.
    """
    if not phrase or not isinstance(phrase, str):
        return None
    text = phrase.lower()
    # Strip currency and boilerplate words
    for junk in ("rupees", "rupee", "inr", "rs.", "rs", "only", "₹", ".", ",", "-"):
        text = text.replace(junk, " ")
    # Split at "and" to separate rupees from paise
    if " and " in text:
        rupee_part, paise_part = text.split(" and ", 1)
    else:
        rupee_part, paise_part = text, ""
    # Further split paise_part on "paise" keyword
    if "paise" in paise_part:
        paise_part = paise_part.split("paise")[0]
    elif "paise" in rupee_part:
        idx = rupee_part.index("paise")
        # rare pattern: paise appears in main text; ignore
        rupee_part = rupee_part[:idx]

    def _words_to_int(s: str) -> int | None:
        tokens = [t for t in s.split() if t]
        if not tokens:
            return None
        total = 0
        current = 0
        saw_any = False
        for tok in tokens:
            if tok in _WORD_UNITS:
                current += _WORD_UNITS[tok]
                saw_any = True
            elif tok == "hundred":
                current = (current or 1) * 100
                saw_any = True
            elif tok in _WORD_SCALES:
                scale = _WORD_SCALES[tok]
                total += (current or 1) * scale
                current = 0
                saw_any = True
            else:
                # Unknown token — skip silently (likely stray word)
                continue
        if not saw_any:
            return None
        return total + current

    rupees = _words_to_int(rupee_part)
    if rupees is None:
        return None
    paise = _words_to_int(paise_part) or 0
    return float(rupees) + (paise / 100.0)


def _words_disagree_with_numeric(extracted: dict) -> bool:
    """Return True if the amount-in-words disagrees with the numeric total by ≥5% (scale error)."""
    phrase = extracted.get("total_amount_in_words") or extracted.get("credit_amount_in_words")
    numeric = extracted.get("total_amount")
    if numeric in (None, "", "null"):
        numeric = extracted.get("credit_amount")
    if numeric in (None, "", "null") or not phrase:
        return False
    parsed = _parse_amount_in_words(phrase)
    if parsed is None or parsed <= 0:
        return False
    try:
        numeric_f = float(numeric)
    except (TypeError, ValueError):
        return False
    if numeric_f <= 0:
        return False
    ratio = max(numeric_f, parsed) / min(numeric_f, parsed)
    # Allow small rounding differences (round-off up to ~1%). 5% catches all scale errors (10×, 100×, 1000×).
    return ratio > 1.05


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
    # Always retry if total amount is missing — it's the most critical field
    total = extracted.get("total_amount")
    if total is None or total in ("null", ""):
        return True
    # Retry if amount-in-words disagrees with numeric total (scale/decimal error)
    if _words_disagree_with_numeric(extracted):
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
        max_tokens=3072,
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

    # Word-form correction: if numeric total disagrees with amount-in-words by a scale factor,
    # trust the words. This catches Haiku/Sonnet decimal-drop errors (e.g. 10200.00 → 10200000).
    words_corrected = False
    if _words_disagree_with_numeric(extracted):
        phrase = extracted.get("total_amount_in_words") or extracted.get("credit_amount_in_words")
        parsed = _parse_amount_in_words(phrase)
        if parsed is not None and parsed > 0:
            if "total_amount" in extracted and extracted.get("total_amount") not in (None, "", "null"):
                extracted["total_amount"] = parsed
                words_corrected = True
            elif "credit_amount" in extracted and extracted.get("credit_amount") not in (None, "", "null"):
                extracted["credit_amount"] = parsed
                words_corrected = True
            if words_corrected:
                note = extracted.get("extraction_notes") or ""
                extracted["extraction_notes"] = (
                    (note + " | " if note else "")
                    + f"Numeric total corrected from word-form ('{phrase}' = {parsed})"
                )

    confidence = extracted.get("extraction_confidence", "low")
    cost_inr = _cost_inr(HAIKU_MODEL, in_tok, out_tok)
    if model_used == SONNET_MODEL:
        cost_inr += _cost_inr(SONNET_MODEL, in_tok2, out_tok2)

    # Flag for review if medium or low confidence, if critical fields are empty, or if we had to correct via words
    vendor_ok = bool(extracted.get("vendor_name") and len(extracted.get("vendor_name", "")) >= 3)
    amount_ok = extracted.get("total_amount") not in (None, "null", "")
    needs_review = confidence in ("low", "medium") or not vendor_ok or not amount_ok or words_corrected

    return ExtractionResult(
        extracted=extracted,
        model_used=model_used,
        input_tokens=in_tok + in_tok2,
        output_tokens=out_tok + out_tok2,
        cost_inr=cost_inr,
        confidence=confidence,
        needs_review=needs_review,
    )
