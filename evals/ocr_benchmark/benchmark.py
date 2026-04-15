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

EXTRACTION_PROMPT = """You are extracting structured data from an Indian business document (tax invoice, credit note, delivery challan, or bill of supply).

STEP 1 — Identify the document type:
Look for these labels at the top of the document:
- "Tax Invoice" → type = "tax_invoice"
- "Credit Note" or "Debit Note" → type = "credit_note"
- "Delivery Challan" → type = "delivery_challan"
- "Bill of Supply" → type = "bill_of_supply"
If unclear, use "tax_invoice" as default.

STEP 2 — Read handwritten portions carefully:
Some fields (quantities, amounts, dates) may be handwritten. Read digit-by-digit.
Common confusion: 0 vs O, 1 vs I, 5 vs S, 8 vs B. Context and surrounding printed text help.

STEP 3 — Extract and validate the GSTIN:
A valid Indian GSTIN is exactly 15 characters: [2-digit state code][10-char PAN][1-digit entity number][Z][1 check digit].
State code 32 = Kerala. State code 33 = Tamil Nadu. State code 27 = Maharashtra.
If you see a 15-character alphanumeric string near "GSTIN" or "GST No", that is it — read it carefully.

STEP 4 — Extract fields based on document type.

For tax_invoice, bill_of_supply, delivery_challan:
{
  "document_type": "tax_invoice",
  "vendor_name": "Name of the seller/issuer",
  "vendor_gstin": "Seller GSTIN (exactly 15 chars)",
  "buyer_name": "Name of the buyer if present",
  "buyer_gstin": "Buyer GSTIN if present",
  "bill_number": "Invoice or bill number",
  "bill_date": "Date in YYYY-MM-DD format",
  "total_amount": "Final total in rupees (numeric only)",
  "taxable_amount": "Pre-tax subtotal if shown (numeric only)",
  "cgst_amount": "CGST amount if present (numeric only, null if IGST is used instead)",
  "sgst_amount": "SGST amount if present (numeric only, null if IGST is used instead)",
  "igst_amount": "IGST amount if present (numeric only, null if CGST/SGST are used instead)",
  "category": "One of: electrical, materials, groceries, services, utilities, medical, transport, other",
  "line_items": [
    {
      "description": "Item name",
      "hsn_code": "HSN/SAC code if present",
      "quantity": "Numeric quantity",
      "unit_price": "Price per unit",
      "amount": "Line total"
    }
  ],
  "field_confidence": {
    "vendor_gstin": "high/medium/low",
    "total_amount": "high/medium/low",
    "tax_amounts": "high/medium/low"
  },
  "extraction_confidence": "high/medium/low",
  "extraction_notes": "Brief note on anything unclear or handwritten"
}

For credit_note or debit_note:
{
  "document_type": "credit_note",
  "vendor_name": "Name of the issuer",
  "vendor_gstin": "Issuer GSTIN (exactly 15 chars)",
  "document_number": "Credit/debit note number",
  "document_date": "Date in YYYY-MM-DD format",
  "original_invoice_number": "The invoice this note is against",
  "original_invoice_date": "Date of original invoice if shown",
  "credit_amount": "Total credit/debit amount (numeric only)",
  "cgst_amount": "CGST adjustment if present (numeric only)",
  "sgst_amount": "SGST adjustment if present (numeric only)",
  "igst_amount": "IGST adjustment if present (numeric only)",
  "reason": "Reason for credit/debit note if stated",
  "category": "One of: electrical, materials, groceries, services, utilities, medical, transport, other",
  "field_confidence": {
    "vendor_gstin": "high/medium/low",
    "credit_amount": "high/medium/low",
    "original_invoice_number": "high/medium/low"
  },
  "extraction_confidence": "high/medium/low",
  "extraction_notes": "Brief note on anything unclear or handwritten"
}

Return ONLY the JSON object, no explanation."""


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


def _needs_sonnet_retry(extracted: dict) -> bool:
    """Return True if the extraction has critical quality issues that warrant a Sonnet retry."""
    confidence = extracted.get("extraction_confidence", "high")
    if confidence == "low":
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
