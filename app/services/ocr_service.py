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
from PIL import Image, ExifTags, ImageFilter, ImageOps, ImageStat

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

_BASE_PROMPT = """You extract structured data from an Indian business document photo (bill, tax invoice, or credit/debit note).
__OWNER_BLOCK__
STEP 1 — Document type (DO THIS FIRST, before any field extraction):
Scan the title/header for these exact phrases:
- "Credit Note", "CDNR", "Cr. Note"   → document_type = "credit_note"
- "Debit Note", "DBNR", "Dr. Note"    → document_type = "debit_note"
- "Tax Invoice"                        → "tax_invoice"
- "Bill of Supply"                     → "bill_of_supply"
- Plain receipt                        → "receipt"
Default: "tax_invoice". Ignore adjacent invoice references — the title at the TOP of the document decides the type.

STEP 2 — Dates (errors here are common, ESPECIALLY on handwritten bills):
Indian bills print/write dates as DD/MM/YY or DD/MM/YYYY. "20/01/26" means 20 January 2026. Year "26" = 2026, "25" = 2025.
NEVER swap day and month. The FIRST group is always the day (1–31); the SECOND is the month (1–12). If you read month > 12, you swapped — undo and re-read.
On handwritten dates, watch for these digit confusions: 0↔6, 1↔7, 2↔7, 5↔6, and "01" (January) vs "12" (December) — a "1" with a heavy serif or closed loop can look like "12".
Return dates as YYYY-MM-DD.

STEP 3 — GSTINs (15-char, format: [2-digit state][5 letters][4 digits][entity letter][Z][check]):
- vendor_gstin = business ISSUING the bill (letterhead at top). Labelled "GSTIN", "GST No", "Supplier GSTIN".
- buyer_gstin = business RECEIVING the bill. Labelled "Bill To", "Buyer", "Consignee", "Customer GSTIN".
- PAN entity letter (char 6 of GSTIN, = 4th of PAN) on BUSINESS letterheads is almost always F (firm), C (company), H (HUF), A (AOP/association), T (trust), B (BOI), L (LLP), J (AJP), G (government). P (individual) is rare on printed GST invoices — if you read P on a letterhead, reconsider and prefer F.
- Common OCR confusions: O↔Q, E↔F, B↔8, 0↔O, 1↔I, S↔5, 2↔Z. Apply the entity-letter rule to disambiguate.
- State codes: Kerala=32, Tamil Nadu=33, Maharashtra=27, Karnataka=29, Delhi=07.
- Never put the buyer GSTIN in vendor_gstin, or vice versa.

STEP 3.5 — Handwritten portions (apply EVERYWHERE a number appears, especially amounts and bill numbers):
If any part of the bill is handwritten, read each digit SEPARATELY before combining. Common confusions on Indian handwriting: 0↔6, 1↔7, 2↔7, 3↔8, 5↔6, 8↔3. For amounts, verify the magnitude feels right for the line items (a 3-digit handwritten "108" with a tall "1" can look like "708"). NEVER return null on a handwritten bill if you can read the digits at all — return a best-guess even with low confidence; the user will review it.

STEP 4 — Amounts (Indian format: ₹1,23,456.78 = 123456.78):
- PRESERVE all decimal digits (paise). ₹1,234.50 → 1234.50, never 1234.
- total_amount = FINAL payable after ALL taxes. Labels (priority order): Grand Total, Invoice Total, Total Amount, Net Payable, Amount Payable, Net Amount. If multiple, use the LAST/LARGEST.
- taxable_amount = pre-tax subtotal.
- Intra-state: cgst_amount == sgst_amount EXACTLY. Use symmetry if one is unclear.
- Math identity: taxable + cgst + sgst + igst ≈ total (allow ₹1 round-off).

STEP 5 — Word-form cross-check (MANDATORY):
Indian bills spell the total in words ("Rupees Ten Thousand Two Hundred Only"). Transcribe the phrase verbatim into total_amount_in_words (or credit_amount_in_words). If your numeric reading disagrees in scale with the words, the WORDS WIN — overwrite and note it.

STEP 6 — Return JSON ONLY. No markdown, no prose.

For tax_invoice / bill_of_supply / receipt:
{
  "document_type": "tax_invoice",
  "vendor_name": "seller business name from letterhead",
  "vendor_gstin": "15-char or null",
  "buyer_name": "... or null",
  "buyer_gstin": "15-char or null",
  "bill_number": "... or null",
  "bill_date": "YYYY-MM-DD or null",
  "total_amount": 1234.56,
  "total_amount_in_words": "Rupees ... Only, or null",
  "taxable_amount": 1000.00,
  "cgst_amount": 90.00,
  "sgst_amount": 90.00,
  "igst_amount": null,
  "tax_slab": "5|12|18|28|Mixed|null",
  "category": "electrical|materials|groceries|services|utilities|medical|transport|other",
  "extraction_notes": "anything unclear (or null)"
}

For credit_note / debit_note:
{
  "document_type": "credit_note",
  "vendor_name": "issuer business name",
  "vendor_gstin": "15-char or null",
  "buyer_gstin": "15-char or null",
  "document_number": "...",
  "document_date": "YYYY-MM-DD",
  "original_invoice_number": "referenced invoice or null",
  "original_invoice_date": "YYYY-MM-DD or null",
  "credit_amount": 500.00,
  "credit_amount_in_words": "Rupees ... Only",
  "taxable_amount": 420.00,
  "cgst_amount": 40.00,
  "sgst_amount": 40.00,
  "igst_amount": null,
  "tax_slab": "5|12|18|28|Mixed|null",
  "category": "electrical|materials|groceries|services|utilities|medical|transport|other",
  "extraction_notes": "anything unclear (or null)"
}

Rules: null (not the string "null"); amounts are numbers not strings; preserve paise; prefer a best-guess over null."""


def _build_prompt(owner_gstin: str | None) -> str:
    if owner_gstin:
        owner = owner_gstin.strip().upper()
        # Position-based guidance: the GSTIN on the TOP/letterhead is always the
        # vendor, regardless of whether it's the owner's or not. This keeps sales
        # bills (where owner == vendor) correct while still letting the model
        # disambiguate purchase bills (where owner == buyer).
        block = (
            f"\nCONTEXT: The user's own GSTIN is `{owner}`. On a bill this user issued (a sales "
            f"bill), `{owner}` appears on the TOP/letterhead as the vendor — put it in vendor_gstin. "
            f"On a bill this user received (a purchase bill), `{owner}` appears next to 'Bill To' / "
            f"'Buyer' — put it in buyer_gstin. ALWAYS decide based on WHERE on the bill you see the "
            f"GSTIN, never assume. Read the top letterhead to find the real vendor_gstin.\n"
        )
    else:
        block = "\n"
    return _BASE_PROMPT.replace("__OWNER_BLOCK__", block.strip("\n"))


@dataclass
class ExtractionResult:
    extracted: dict
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_inr: float
    confidence: str = "high"
    needs_review: bool = False
    needs_manual_entry: bool = False


_CRITICAL_FIELDS_TAX_INVOICE = ("vendor_name", "total_amount", "bill_date")
_CRITICAL_FIELDS_CREDIT_NOTE = ("vendor_name", "credit_amount", "document_date")


def _is_ocr_blank(extracted: dict) -> bool:
    """Return True when even Sonnet couldn't read the critical fields off the bill.

    "Blank" means every one of the 3 critical fields (vendor + amount + date) is
    null/empty. Hit primarily by illegible handwritten bills — billsample3 in
    the eval set is the canonical example. Lets the UI route these to a manual-
    entry form rather than show an empty "review" screen that frustrates users.
    """
    doc_type = (extracted.get("document_type") or "").lower()
    fields = _CRITICAL_FIELDS_CREDIT_NOTE if doc_type in ("credit_note", "debit_note") else _CRITICAL_FIELDS_TAX_INVOICE
    return all(extracted.get(f) in (None, "", "null") for f in fields)


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


_MAX_IMAGE_DIM = 1600


def _downscale_image(image_bytes: bytes, max_dim: int = _MAX_IMAGE_DIM) -> bytes:
    """Resize so the long edge is <= max_dim. Cuts input tokens ~3-4x on phone photos."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        longest = max(w, h)
        if longest <= max_dim:
            return image_bytes
        scale = max_dim / longest
        new_size = (int(w * scale), int(h * scale))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        resized = img.resize(new_size, Image.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        return image_bytes


def _enhance_for_ocr(image_bytes: bytes) -> bytes:
    """Enhance handwritten / low-contrast bills.

    When the image has low tonal spread (std-dev < 55 on an L-channel), apply
    PIL autocontrast + a mild unsharp mask to make handwritten strokes pop.
    Printed bills with good contrast pass through unchanged.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        stat = ImageStat.Stat(img.convert("L"))
        stddev = stat.stddev[0] if stat.stddev else 0
        if stddev >= 55:
            return image_bytes  # already crisp; don't touch
        enhanced = ImageOps.autocontrast(img, cutoff=1)
        enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
        buf = io.BytesIO()
        enhanced.save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception:
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


def _needs_sonnet_retry(extracted: dict, owner_gstin: str | None = None) -> bool:
    """Structural gate: retry Sonnet only when extraction is objectively broken.

    Self-reported "medium" confidence alone is NOT enough — Haiku over-reports
    medium, which caused 5/8 bills to trigger fallback in the baseline. Retry only
    when a required field is null/invalid, the word-form disagrees with the total,
    or the vendor_gstin is the OWNER's GSTIN (model echoed the prompt hint).
    """
    vendor = extracted.get("vendor_name") or ""
    if not vendor or len(vendor) < 3 or vendor.lower() in ("unknown", "null", "n/a"):
        return True

    # Credit/debit notes use credit_amount; tax_invoice et al. use total_amount.
    doc_type = (extracted.get("document_type") or "").lower()
    amount_key = "credit_amount" if doc_type in ("credit_note", "debit_note") else "total_amount"
    amount = extracted.get(amount_key)
    if amount in (None, "", "null"):
        return True

    vendor_gstin = extracted.get("vendor_gstin")
    if vendor_gstin and not _is_valid_gstin(vendor_gstin):
        return True

    # Guard against the model echoing the owner GSTIN straight into vendor_gstin.
    # Observed on 3/8 bills in the Stage 1 first pass.
    if owner_gstin and vendor_gstin:
        if vendor_gstin.strip().upper() == owner_gstin.strip().upper():
            return True

    if _words_disagree_with_numeric(extracted):
        return True

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


async def _call_claude(
    image_bytes: bytes, content_type: str, model: str, prompt: str
) -> tuple[dict, int, int]:
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
        max_tokens=1200,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_data},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    extracted = _parse_json_response(message.content[0].text)
    return extracted, message.usage.input_tokens, message.usage.output_tokens


async def extract(
    image_bytes: bytes,
    content_type: str,
    owner_gstin: str | None = None,
) -> ExtractionResult:
    """Extract GST fields from a bill image.

    1. Fixes EXIF orientation so mobile photos are right-side up.
    2. Tries Haiku first for cost efficiency.
    3. Retries with Sonnet only on structural failure (missing/invalid required field).

    ``owner_gstin`` — if provided, is injected into the prompt so the model places
    the user's own GSTIN in buyer_gstin rather than confusing it with the vendor.
    """
    image_bytes = _fix_orientation(image_bytes)
    image_bytes = _downscale_image(image_bytes)
    image_bytes = _enhance_for_ocr(image_bytes)
    prompt = _build_prompt(owner_gstin)

    # First pass — Haiku
    extracted, in_tok, out_tok = await _call_claude(image_bytes, content_type, HAIKU_MODEL, prompt)
    model_used = HAIKU_MODEL
    in_tok2, out_tok2 = 0, 0

    # Sonnet fallback (structural only)
    if _needs_sonnet_retry(extracted, owner_gstin):
        extracted2, in_tok2, out_tok2 = await _call_claude(
            image_bytes, content_type, SONNET_MODEL, prompt
        )
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

    # Manual-entry cohort: both models failed to read vendor + amount + date.
    # Surface this so the UI can show an "OCR couldn't read this — please type it in"
    # state instead of an empty review form.
    needs_manual_entry = _is_ocr_blank(extracted)
    if needs_manual_entry:
        note = extracted.get("extraction_notes") or ""
        extracted["extraction_notes"] = (
            (note + " | " if note else "")
            + "MANUAL_ENTRY_REQUIRED: OCR could not read the key fields; user must enter manually."
        )

    # Flag for review if medium or low confidence, if critical fields are empty, or if we had to correct via words
    vendor_ok = bool(extracted.get("vendor_name") and len(extracted.get("vendor_name", "")) >= 3)
    amount_ok = extracted.get("total_amount") not in (None, "null", "")
    needs_review = (
        confidence in ("low", "medium") or not vendor_ok or not amount_ok or words_corrected
    )

    return ExtractionResult(
        extracted=extracted,
        model_used=model_used,
        input_tokens=in_tok + in_tok2,
        output_tokens=out_tok + out_tok2,
        cost_inr=cost_inr,
        confidence=confidence,
        needs_review=needs_review,
        needs_manual_entry=needs_manual_entry,
    )
