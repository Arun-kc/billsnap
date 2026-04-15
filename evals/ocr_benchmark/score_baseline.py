"""
Score the current production OCR pipeline against ground_truth.yaml.

Measures:
- Perspective classification correctness (purchase / sales / credit_note)
- Per-field accuracy (vendor_name, vendor_gstin, bill_number, bill_date,
  total_amount, taxable_amount, cgst_amount, sgst_amount)
- Latency (seconds) and cost (INR) per bill, with aggregates.

Runs as an ad-hoc script from the repo root:
    python3 evals/ocr_benchmark/score_baseline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

import anthropic  # noqa: E402

from app.services import ocr_service  # noqa: E402


async def _extract_with_retry(
    image_bytes: bytes, owner_gstin: str, attempts: int = 4
) -> ocr_service.ExtractionResult:
    """Retry the extraction on 529 Overloaded with exponential backoff."""
    delay = 15.0
    for attempt in range(attempts):
        try:
            return await ocr_service.extract(image_bytes, "image/jpeg", owner_gstin=owner_gstin)
        except anthropic.APIStatusError as e:
            # 529 Overloaded is transient; retry with backoff. Other status errors bubble up.
            if getattr(e, "status_code", None) not in (429, 529) or attempt == attempts - 1:
                raise
            print(f"   (Anthropic {e.status_code} — retrying in {delay:.0f}s)")
            await asyncio.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")

SAMPLE_DIR = Path(__file__).parent / "sample_bills"
GROUND_TRUTH = SAMPLE_DIR / "ground_truth.yaml"

SCORED_FIELDS = [
    "bill_number",
    "bill_date",
    "vendor_name",
    "vendor_gstin",
    "total_amount",
    "taxable_amount",
    "cgst_amount",
    "sgst_amount",
]


@dataclass(frozen=True)
class FieldVerdict:
    name: str
    expected: object
    actual: object
    passed: bool


def classify_perspective(extracted: dict, owner_gstin: str) -> str:
    """Infer bill perspective from extraction + owner GSTIN. Mirrors the logic we'll put in the classifier service."""
    doc_type = (extracted.get("document_type") or "").lower()
    if doc_type in {"credit_note", "debit_note"}:
        return "credit_note"

    owner = (owner_gstin or "").upper().strip()
    vendor_g = (extracted.get("vendor_gstin") or "").upper().strip()
    buyer_g = (extracted.get("buyer_gstin") or "").upper().strip()

    if owner and vendor_g == owner:
        return "sales"
    if owner and buyer_g == owner:
        return "purchase"
    return "unknown"


def normalize_gstin(value: object) -> str | None:
    if not value or not isinstance(value, str):
        return None
    return value.upper().strip()


def normalize_bill_number(value: object) -> str | None:
    if value in (None, "", "null"):
        return None
    return str(value).strip().upper().replace(" ", "")


def normalize_date(value: object) -> str | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    s = str(value).strip()
    # Accept ISO already
    try:
        return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
    except ValueError:
        pass
    return s


def amount_close(actual: object, expected: object, tol: float = 0.50) -> bool:
    """Amounts match if within ±₹0.50 (round-off tolerance)."""
    if expected is None:
        return actual in (None, "", "null")
    if actual in (None, "", "null"):
        return False
    try:
        return abs(float(actual) - float(expected)) <= tol
    except (TypeError, ValueError):
        return False


def vendor_name_close(actual: object, expected: object) -> bool:
    if expected is None:
        return True
    if not actual:
        return False
    a = str(actual).strip().upper()
    e = str(expected).strip().upper()
    return a == e or a.startswith(e) or e.startswith(a) or e in a or a in e


def score_field(name: str, actual: object, expected: object) -> FieldVerdict:
    if expected is None:
        return FieldVerdict(name, expected, actual, True)  # not in ground truth → skip

    if name == "vendor_gstin":
        passed = normalize_gstin(actual) == normalize_gstin(expected)
    elif name == "bill_number":
        passed = normalize_bill_number(actual) == normalize_bill_number(expected)
    elif name == "bill_date":
        passed = normalize_date(actual) == normalize_date(expected)
    elif name == "vendor_name":
        passed = vendor_name_close(actual, expected)
    elif name in {"total_amount", "taxable_amount", "cgst_amount", "sgst_amount"}:
        passed = amount_close(actual, expected)
    else:
        passed = actual == expected
    return FieldVerdict(name, expected, actual, passed)


async def run() -> None:
    spec = yaml.safe_load(GROUND_TRUTH.read_text())
    owner_gstin = spec["owner"]["gstin"]
    fixtures = spec["fixtures"]

    header_fmt = "{:<20} {:<12} {:<10} {:<8} {:<9}"
    print(header_fmt.format("BILL", "PERSPECTIVE", "FIELDS", "LATENCY", "COST ₹"))
    print("-" * 62)

    total_latency = 0.0
    total_cost = 0.0
    total_fields_pass = 0
    total_fields_checked = 0
    perspective_hits = 0
    perspective_total = 0
    per_bill_verdicts: list[dict] = []

    for fx in fixtures:
        img_path = SAMPLE_DIR / fx["file"]
        image_bytes = img_path.read_bytes()

        t0 = time.perf_counter()
        result = await _extract_with_retry(image_bytes, owner_gstin)
        elapsed = time.perf_counter() - t0

        total_latency += elapsed
        total_cost += result.cost_inr

        inferred = classify_perspective(result.extracted, owner_gstin)
        expected_persp = fx["perspective"]
        perspective_total += 1
        persp_ok = inferred == expected_persp
        if persp_ok:
            perspective_hits += 1

        field_verdicts: list[FieldVerdict] = []
        for field in SCORED_FIELDS:
            if field in fx:
                # For credit notes the extractor uses document_number / document_date / credit_amount.
                actual = result.extracted.get(field)
                if actual in (None, "", "null") and expected_persp == "credit_note":
                    if field == "bill_number":
                        actual = result.extracted.get("document_number")
                    elif field == "bill_date":
                        actual = result.extracted.get("document_date")
                    elif field == "total_amount":
                        actual = result.extracted.get("credit_amount")
                verdict = score_field(field, actual, fx.get(field))
                field_verdicts.append(verdict)

        passed = sum(1 for v in field_verdicts if v.passed)
        checked = len(field_verdicts)
        total_fields_pass += passed
        total_fields_checked += checked

        print(
            header_fmt.format(
                fx["file"],
                f"{'✓' if persp_ok else '✗'} {inferred}/{expected_persp}",
                f"{passed}/{checked}",
                f"{elapsed:4.1f}s",
                f"{result.cost_inr:.3f}",
            )
        )
        for v in field_verdicts:
            if not v.passed:
                print(f"   ✗ {v.name:<16} expected={v.expected!r:<25} got={v.actual!r}")

        per_bill_verdicts.append(
            {
                "file": fx["file"],
                "perspective_expected": expected_persp,
                "perspective_inferred": inferred,
                "perspective_ok": persp_ok,
                "latency_s": round(elapsed, 2),
                "cost_inr": result.cost_inr,
                "model_used": result.model_used,
                "confidence": result.confidence,
                "fields": [
                    {
                        "name": v.name,
                        "expected": v.expected if not isinstance(v.expected, date) else v.expected.isoformat(),
                        "actual": v.actual,
                        "passed": v.passed,
                    }
                    for v in field_verdicts
                ],
                "extraction_notes": result.extracted.get("extraction_notes"),
            }
        )

    print("=" * 62)
    n = len(fixtures)
    field_pct = (100 * total_fields_pass / total_fields_checked) if total_fields_checked else 0
    persp_pct = (100 * perspective_hits / perspective_total) if perspective_total else 0
    print(
        f"SUMMARY  perspectives {perspective_hits}/{perspective_total} ({persp_pct:.0f}%)  "
        f"fields {total_fields_pass}/{total_fields_checked} ({field_pct:.0f}%)  "
        f"avg {total_latency / n:.1f}s  avg ₹{total_cost / n:.3f}  total ₹{total_cost:.2f}"
    )

    report_path = Path(__file__).parent / "results" / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(
        json.dumps(
            {
                "owner_gstin": owner_gstin,
                "summary": {
                    "perspective_accuracy": persp_pct,
                    "field_accuracy": field_pct,
                    "avg_latency_s": round(total_latency / n, 2),
                    "avg_cost_inr": round(total_cost / n, 4),
                    "total_cost_inr": round(total_cost, 4),
                },
                "bills": per_bill_verdicts,
            },
            indent=2,
            default=str,
        )
    )
    print(f"\nDetail: {report_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    asyncio.run(run())
