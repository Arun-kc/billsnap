"""
BillSnap — OCR Vendor Benchmark
Compares Claude Vision (Haiku) vs AWS Textract on real Indian GST bills.

Usage:
  1. Drop bill images (.jpg, .jpeg, .png, .pdf) into sample_bills/
  2. Copy .env.example to .env and fill in your API keys
  3. Run: python benchmark.py
  4. Results are saved to results/report.json and printed as a table
"""

import base64
import json
import os
import time
from pathlib import Path
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

SAMPLE_DIR = Path(__file__).parent / "sample_bills"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Fields scored for tax invoices
INVOICE_FIELDS = [
    "vendor_name",
    "vendor_gstin",
    "bill_number",
    "bill_date",
    "total_amount",
    "cgst_amount",
    "sgst_amount",
    "tax_amount",   # satisfied by CGST+SGST or IGST — ensures at least one tax field present
    "category",
]

# Fields scored for credit notes
CREDIT_NOTE_FIELDS = [
    "vendor_name",
    "vendor_gstin",
    "document_number",
    "document_date",
    "credit_amount",
    "original_invoice_number",
    "category",
]

# Haiku handles most bills; Sonnet is the fallback for low-confidence results
HAIKU_MODEL  = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-6"

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


def load_image_as_base64(image_path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) for a bill image."""
    suffix = image_path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


def _call_claude(model: str, image_data: str, media_type: str) -> tuple[dict, int, int, float]:
    """Call Claude vision with the extraction prompt. Returns (extracted, input_tokens, output_tokens, elapsed)."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    start = time.perf_counter()
    message = client.messages.create(
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
    elapsed = time.perf_counter() - start

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        extracted = {"_parse_error": raw}

    return extracted, message.usage.input_tokens, message.usage.output_tokens, elapsed


def _is_valid_gstin(gstin: str | None) -> bool:
    """A valid GSTIN is exactly 15 chars: 2-digit state code + 10-char PAN + 1 entity + Z + 1 check."""
    if not gstin or gstin in ("null", ""):
        return False
    import re
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


def _parse_amount_in_words(phrase):
    if not phrase or not isinstance(phrase, str):
        return None
    text = phrase.lower()
    for junk in ("rupees", "rupee", "inr", "rs.", "rs", "only", "₹", ".", ",", "-"):
        text = text.replace(junk, " ")
    if " and " in text:
        rupee_part, paise_part = text.split(" and ", 1)
    else:
        rupee_part, paise_part = text, ""
    if "paise" in paise_part:
        paise_part = paise_part.split("paise")[0]

    def _words_to_int(s):
        tokens = [t for t in s.split() if t]
        if not tokens:
            return None
        total, current, saw_any = 0, 0, False
        for tok in tokens:
            if tok in _WORD_UNITS:
                current += _WORD_UNITS[tok]
                saw_any = True
            elif tok == "hundred":
                current = (current or 1) * 100
                saw_any = True
            elif tok in _WORD_SCALES:
                total += (current or 1) * _WORD_SCALES[tok]
                current = 0
                saw_any = True
        if not saw_any:
            return None
        return total + current

    rupees = _words_to_int(rupee_part)
    if rupees is None:
        return None
    paise = _words_to_int(paise_part) or 0
    return float(rupees) + (paise / 100.0)


def _words_disagree_with_numeric(extracted):
    phrase = extracted.get("total_amount_in_words") or extracted.get("credit_amount_in_words")
    numeric = extracted.get("total_amount") or extracted.get("credit_amount")
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
    return ratio > 1.05


def _needs_sonnet_retry(extracted: dict) -> bool:
    """Return True if the extraction has critical quality issues that warrant a Sonnet retry."""
    confidence = extracted.get("extraction_confidence", "high")
    if confidence == "low":
        return True
    # Always retry if total amount is missing — it's the most critical field
    total = extracted.get("total_amount")
    if total is None or total in ("null", ""):
        return True
    # Retry if amount-in-words disagrees with numeric total (scale/decimal error)
    if _words_disagree_with_numeric(extracted):
        return True
    if confidence == "medium":
        gstin = extracted.get("vendor_gstin")
        gstin_invalid = not _is_valid_gstin(gstin)
        tax_missing = (
            extracted.get("cgst_amount") in (None, "", "null") and
            extracted.get("sgst_amount") in (None, "", "null") and
            extracted.get("igst_amount") in (None, "", "null")
        )
        return gstin_invalid or tax_missing
    return False


def _model_cost_inr(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in INR. Prices per million tokens."""
    pricing = {
        HAIKU_MODEL:  (0.80, 4.00),   # input, output USD/M
        SONNET_MODEL: (3.00, 15.00),
    }
    input_price, output_price = pricing.get(model, (3.00, 15.00))
    cost_usd = (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    return round(cost_usd * 84, 4)


def extract_with_claude(image_path: Path, sonnet_fallback: bool = True) -> dict:
    """Extract GST fields using Claude Haiku, with optional Sonnet fallback for low-confidence results."""
    image_data, media_type = load_image_as_base64(image_path)

    # First pass — Haiku
    extracted, in_tok, out_tok, elapsed = _call_claude(HAIKU_MODEL, image_data, media_type)
    model_used = HAIKU_MODEL
    total_in_tok, total_out_tok, total_elapsed = in_tok, out_tok, elapsed

    # Sonnet fallback if confidence is low OR critical fields are suspect
    if sonnet_fallback and _needs_sonnet_retry(extracted):
        print(f"(low confidence — retrying with Sonnet) ", end="", flush=True)
        extracted2, in_tok2, out_tok2, elapsed2 = _call_claude(SONNET_MODEL, image_data, media_type)
        # Use Sonnet result if it's better or equal
        if extracted2.get("extraction_confidence", "low") != "low" or not extracted.get("vendor_name"):
            extracted = extracted2
            model_used = SONNET_MODEL
        total_in_tok  += in_tok2
        total_out_tok += out_tok2
        total_elapsed += elapsed2

    # Word-form correction: trust the amount-in-words over the numeric reading for scale errors
    if _words_disagree_with_numeric(extracted):
        phrase = extracted.get("total_amount_in_words") or extracted.get("credit_amount_in_words")
        parsed = _parse_amount_in_words(phrase)
        if parsed is not None and parsed > 0:
            old_total = extracted.get("total_amount") or extracted.get("credit_amount")
            if extracted.get("total_amount") not in (None, "", "null"):
                extracted["total_amount"] = parsed
            elif extracted.get("credit_amount") not in (None, "", "null"):
                extracted["credit_amount"] = parsed
            note = extracted.get("extraction_notes") or ""
            extracted["extraction_notes"] = (note + " | " if note else "") + f"Corrected via word-form: {old_total} → {parsed} (words: '{phrase}')"
            print(f"(word-form correction: {old_total} → {parsed}) ", end="", flush=True)

    cost_inr = _model_cost_inr(HAIKU_MODEL, in_tok, out_tok)
    if model_used == SONNET_MODEL:
        cost_inr += _model_cost_inr(SONNET_MODEL, in_tok2, out_tok2)

    return {
        "vendor": "claude-haiku" if model_used == HAIKU_MODEL else "claude-haiku+sonnet",
        "extracted": extracted,
        "latency_s": round(total_elapsed, 2),
        "input_tokens": total_in_tok,
        "output_tokens": total_out_tok,
        "cost_inr": cost_inr,
        "model_used": model_used,
    }


def extract_with_textract(image_path: Path) -> dict:
    """Extract fields using AWS Textract AnalyzeExpense."""
    try:
        import boto3
    except ImportError:
        return {"vendor": "aws-textract", "error": "boto3 not installed"}

    client = boto3.client(
        "textract",
        region_name=os.environ.get("AWS_REGION", "ap-south-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    start = time.perf_counter()
    response = client.analyze_expense(Document={"Bytes": image_bytes})
    elapsed = time.perf_counter() - start

    # Flatten Textract's expense fields into our schema
    extracted = {}
    field_map = {
        "VENDOR_NAME": "vendor_name",
        "INVOICE_RECEIPT_ID": "bill_number",
        "INVOICE_RECEIPT_DATE": "bill_date",
        "AMOUNT_DUE": "total_amount",
        "TAX": "cgst_amount",  # Textract doesn't split CGST/SGST
    }
    for doc in response.get("ExpenseDocuments", []):
        for field in doc.get("SummaryFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")
            if field_type in field_map and value:
                extracted[field_map[field_type]] = value

    extracted["extraction_confidence"] = "medium"  # Textract has no confidence score for expenses

    # Textract AnalyzeExpense: $0.05/page
    cost_usd = 0.05

    return {
        "vendor": "aws-textract",
        "extracted": extracted,
        "latency_s": round(elapsed, 2),
        "cost_usd": cost_usd,
        "cost_inr": round(cost_usd * 84, 4),
    }


def score_extraction(extracted: dict) -> dict:
    """Score completeness using the correct field set for the document type."""
    doc_type = extracted.get("document_type", "tax_invoice")
    fields = CREDIT_NOTE_FIELDS if doc_type == "credit_note" else INVOICE_FIELDS

    # tax_amount: satisfied if CGST+SGST both present (intra-state) OR IGST present (inter-state)
    def field_present(f: str) -> bool:
        if f == "tax_amount":
            has_cgst_sgst = (
                extracted.get("cgst_amount") not in (None, "", "null") and
                extracted.get("sgst_amount") not in (None, "", "null")
            )
            has_igst = extracted.get("igst_amount") not in (None, "", "null")
            return has_cgst_sgst or has_igst
        if f == "credit_amount":
            return extracted.get("credit_amount") not in (None, "", "null")
        return extracted.get(f) not in (None, "", "null")

    found = sum(1 for f in fields if field_present(f))
    return {
        "fields_found": found,
        "fields_total": len(fields),
        "completeness_pct": round(100 * found / len(fields), 1),
        "document_type": doc_type,
    }


def run_benchmark(vendors: list[str] = None) -> None:
    if vendors is None:
        vendors = ["claude-haiku"]
        if os.environ.get("AWS_ACCESS_KEY_ID"):
            vendors.append("aws-textract")

    images = sorted(
        p for p in SAMPLE_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )

    if not images:
        print(f"\nNo images found in {SAMPLE_DIR}")
        print("Drop some bill photos (.jpg / .png) there and re-run.\n")
        return

    print(f"\nBenchmarking {len(images)} bill(s) across {len(vendors)} vendor(s)...\n")

    all_results = []
    summary_rows = []

    for image_path in images:
        print(f"  Processing: {image_path.name}")
        bill_results = {"bill": image_path.name, "vendors": {}}

        for vendor in vendors:
            print(f"    → {vendor} ... ", end="", flush=True)
            try:
                if vendor == "claude-haiku":
                    result = extract_with_claude(image_path, sonnet_fallback=True)
                elif vendor == "aws-textract":
                    result = extract_with_textract(image_path)
                else:
                    result = {"vendor": vendor, "error": "unknown vendor"}

                score = score_extraction(result.get("extracted", {}))
                result.update(score)
                bill_results["vendors"][vendor] = result
                print(f"{score['completeness_pct']}% complete  ({result.get('latency_s', '?')}s  ₹{result.get('cost_inr', '?')})")

                summary_rows.append([
                    image_path.name,
                    result.get("vendor", vendor),
                    score.get("document_type", "tax_invoice"),
                    f"{score['completeness_pct']}%",
                    f"{score['fields_found']}/{score['fields_total']}",
                    f"{result.get('latency_s', '?')}s",
                    f"₹{result.get('cost_inr', '?')}",
                    result.get("extracted", {}).get("extraction_confidence", "—"),
                ])
            except Exception as e:
                print(f"ERROR: {e}")
                bill_results["vendors"][vendor] = {"error": str(e)}

        all_results.append(bill_results)

    # Print summary table
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    print(tabulate(
        summary_rows,
        headers=["Bill", "Vendor", "Doc Type", "Complete", "Fields", "Latency", "Cost", "Confidence"],
        tablefmt="rounded_outline",
    ))

    # Cost projection
    print("\nCOST PROJECTION (100 bills/month)")
    print("-" * 40)
    for vendor in vendors:
        vendor_rows = [r for r in summary_rows if r[1] == vendor]
        if vendor_rows:
            avg_cost_str = vendor_rows[0][5].replace("₹", "")
            try:
                avg_cost = float(avg_cost_str)
                monthly = round(avg_cost * 100, 2)
                print(f"  {vendor}: ₹{monthly}/month (100 bills)")
            except ValueError:
                pass

    # Save full results to JSON
    output_path = RESULTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nFull extraction details saved to: {output_path}\n")


if __name__ == "__main__":
    run_benchmark()
