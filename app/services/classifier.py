"""
Bill perspective classifier.

Given an OCR extraction and the owner's GSTIN, infer whether the bill is:
- credit_note  — any credit/debit note document type
- sales        — owner's GSTIN appears as vendor (owner issued this bill)
- purchase     — owner's GSTIN appears as buyer (owner received this bill)
- unknown      — owner GSTIN not provided, or no GSTIN match found

Keeping this pure and dependency-free makes it easy to test and to call from
both the worker (with user.gstin) and the benchmark harness (with a YAML owner).
"""

from typing import Literal

Perspective = Literal["purchase", "sales", "credit_note", "unknown"]


def _norm(value: object) -> str:
    if not value or not isinstance(value, str):
        return ""
    return value.upper().strip()


def classify(extracted: dict, owner_gstin: str | None) -> Perspective:
    """Return the bill perspective from an OCR extraction + owner GSTIN."""
    doc_type = (extracted.get("document_type") or "").lower()
    if doc_type in {"credit_note", "debit_note"}:
        return "credit_note"

    owner = _norm(owner_gstin)
    if not owner:
        return "unknown"

    vendor = _norm(extracted.get("vendor_gstin"))
    buyer = _norm(extracted.get("buyer_gstin"))

    if vendor == owner:
        return "sales"
    if buyer == owner:
        return "purchase"
    return "unknown"
