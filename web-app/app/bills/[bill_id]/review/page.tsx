"use client";

import { useEffect, useState, use, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { getBill, updateBill, type BillDetail } from "@/lib/api";
import { formatAmount, parseAmount } from "@/lib/currency";
import CategoryPicker from "@/components/review/CategoryPicker";
import DatePicker, { formatForDisplay } from "@/components/review/DatePicker";
import TaxBreakdownGroup from "@/components/review/TaxBreakdownGroup";
import StickyFooter from "@/components/ui/StickyFooter";

const DOCUMENT_TYPES = [
  { value: "tax_invoice", label: "Tax Invoice" },
  { value: "bill_of_supply", label: "Bill of Supply" },
  { value: "credit_note", label: "Credit Note" },
  { value: "debit_note", label: "Debit Note" },
  { value: "receipt", label: "Receipt" },
  { value: "other", label: "Other" },
];

function FieldWrapper({
  label,
  lowConfidence = false,
  children,
}: {
  label: string;
  lowConfidence?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`flex flex-col gap-1.5 ${lowConfidence ? "border-l-4 pl-3" : ""}`}
      style={lowConfidence ? { borderColor: "var(--color-warning)" } : undefined}
    >
      <label className="text-xs font-medium text-[var(--color-text-muted)]">
        {label}
        {lowConfidence && (
          <span className="ml-1.5 text-[var(--color-warning)]" title="We're not fully sure — please check">
            ⚠
          </span>
        )}
      </label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full h-12 rounded-xl border border-[var(--color-border)] px-4 bg-white text-[var(--color-text)] focus:outline-none focus:border-[var(--color-aubergine)] transition-colors";

function ReviewContent({ bill_id }: { bill_id: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const ocrFailed = searchParams.get("error") === "ocr_failed";

  const [bill, setBill] = useState<BillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showMore, setShowMore] = useState(false);
  const [catOpen, setCatOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);

  // Editable fields
  const [vendorName, setVendorName] = useState("");
  const [billDate, setBillDate] = useState<string | undefined>(undefined);
  const [totalAmount, setTotalAmount] = useState<number | undefined>(undefined);
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [billNumber, setBillNumber] = useState("");
  const [documentType, setDocumentType] = useState("tax_invoice");
  const [vendorGstin, setVendorGstin] = useState("");
  const [taxableAmount, setTaxableAmount] = useState<number | undefined>(undefined);
  const [cgstAmount, setCgstAmount] = useState(0);
  const [sgstAmount, setSgstAmount] = useState(0);
  const [igstAmount, setIgstAmount] = useState(0);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (bill_id === "new") {
      setLoading(false);
      return;
    }
    getBill(bill_id)
      .then((b) => {
        setBill(b);
        setVendorName(b.vendor_name ?? "");
        setBillDate(b.bill_date ?? undefined);
        setTotalAmount(b.total_amount ?? undefined);
        setCategory(b.category ?? undefined);
        setBillNumber(b.bill_number ?? "");
        setDocumentType(b.document_type ?? "tax_invoice");
        setVendorGstin(b.vendor_gstin ?? "");
        setTaxableAmount(b.taxable_amount ?? undefined);
        setCgstAmount(b.cgst_amount ?? 0);
        setSgstAmount(b.sgst_amount ?? 0);
        setIgstAmount(b.igst_amount ?? 0);
        setNotes(b.user_notes ?? "");
      })
      .catch(() => {
        // If fetch fails, treat as new/blank
      })
      .finally(() => setLoading(false));
  }, [bill_id]);

  const isLowConf = (field: string) => {
    if (!bill?.extraction_confidence) return false;
    // If overall confidence is low (< 0.50), flag critical fields
    if (bill.extraction_confidence < 0.50) {
      return ["vendor_name", "total_amount", "vendor_gstin", "bill_date"].includes(field);
    }
    return false;
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (bill_id !== "new") {
        await updateBill(bill_id, {
          vendor_name: vendorName || undefined,
          bill_date: billDate,
          total_amount: totalAmount,
          category,
          bill_number: billNumber || undefined,
          document_type: documentType,
          vendor_gstin: vendorGstin || undefined,
          taxable_amount: taxableAmount,
          cgst_amount: cgstAmount,
          sgst_amount: sgstAmount,
          igst_amount: igstAmount,
          user_notes: notes || undefined,
          is_verified: true,
        });
        router.replace(`/bills/${bill_id}/done`);
      }
    } catch {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">
        Loading…
      </div>
    );
  }

  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 pt-safe-top py-4 border-b border-[var(--color-border)]">
        <button
          onClick={() => router.back()}
          className="text-[var(--color-text-secondary)] text-sm font-medium min-w-[44px] min-h-[44px] flex items-center"
        >
          ← Back
        </button>
        <span className="text-sm font-medium text-[var(--color-text-muted)]">
          Step 2 / 3
        </span>
      </header>

      <div className="flex flex-col gap-5 px-5 pt-5 pb-32">
        {/* OCR failed banner */}
        {ocrFailed && (
          <div className="rounded-xl border border-[var(--color-info)] bg-[var(--color-info-bg)] p-4 text-sm text-[var(--color-info)]">
            ℹ️ We couldn&apos;t read this bill clearly. Please fill in the details below.
          </div>
        )}

        {/* Bill thumbnail + vendor summary */}
        {bill?.thumbnail_url && (
          <div className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-[var(--color-border)]">
            <div className="relative w-[60px] h-[80px] rounded-lg overflow-hidden flex-shrink-0 bg-[var(--color-surface-2)]">
              <Image
                src={bill.thumbnail_url}
                alt="Bill thumbnail"
                fill
                className="object-cover"
                sizes="60px"
              />
            </div>
            <div className="flex flex-col gap-0.5 justify-center py-1">
              <p className="text-base font-semibold text-[var(--color-text)] leading-snug">
                {vendorName || "Unknown Vendor"}
              </p>
              {billDate && (
                <p className="text-sm text-[var(--color-text-muted)]">
                  {formatForDisplay(billDate)}
                </p>
              )}
            </div>
          </div>
        )}

        <div className="h-px bg-[var(--color-border)]" />

        {/* ── Primary fields ── */}
        <FieldWrapper label="Vendor Name" lowConfidence={isLowConf("vendor_name")}>
          <input
            type="text"
            className={inputClass}
            style={{ fontSize: "var(--text-lg)" }}
            value={vendorName}
            onChange={(e) => setVendorName(e.target.value)}
            placeholder="e.g. Sharma Electricals"
          />
        </FieldWrapper>

        <FieldWrapper label="Date" lowConfidence={isLowConf("bill_date")}>
          <button
            type="button"
            onClick={() => setDateOpen(true)}
            className={`${inputClass} flex items-center justify-between text-left`}
            style={{ fontSize: "var(--text-base)" }}
          >
            <span className={billDate ? "text-[var(--color-text)]" : "text-[var(--color-text-muted)]"}>
              {billDate ? formatForDisplay(billDate) : "Select date"}
            </span>
            <span className="text-[var(--color-text-muted)]">📅</span>
          </button>
        </FieldWrapper>

        <FieldWrapper label="Total Amount (₹)" lowConfidence={isLowConf("total_amount")}>
          <input
            type="number"
            inputMode="decimal"
            className={`${inputClass} font-semibold`}
            style={{ fontSize: "1.375rem" /* 22sp */ }}
            value={totalAmount !== undefined ? formatAmount(totalAmount) : ""}
            onChange={(e) => setTotalAmount(parseAmount(e.target.value))}
            placeholder="0.00"
          />
        </FieldWrapper>

        <FieldWrapper label="Category">
          <button
            type="button"
            onClick={() => setCatOpen(true)}
            className={`${inputClass} flex items-center justify-between text-left`}
          >
            <span className={category ? "text-[var(--color-text)]" : "text-[var(--color-text-muted)]"}>
              {category ?? "Select category"}
            </span>
            <span className="text-[var(--color-text-muted)] text-sm">▼</span>
          </button>
        </FieldWrapper>

        {/* ── More details (collapsible) ── */}
        <button
          type="button"
          onClick={() => setShowMore((v) => !v)}
          className="flex items-center justify-between text-sm font-medium text-[var(--color-aubergine)] min-h-[44px]"
        >
          {showMore ? "▲ Less details" : "▼ More details"}
        </button>

        {showMore && (
          <div className="flex flex-col gap-5 animate-slide-up">
            <FieldWrapper label="Bill Number">
              <input
                type="text"
                className={inputClass}
                value={billNumber}
                onChange={(e) => setBillNumber(e.target.value)}
                placeholder="e.g. INV-2026-042"
              />
            </FieldWrapper>

            <FieldWrapper label="Document Type">
              <select
                className={inputClass}
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
              >
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </FieldWrapper>

            <FieldWrapper label="Vendor GSTIN" lowConfidence={isLowConf("vendor_gstin")}>
              <input
                type="text"
                className={`${inputClass} uppercase`}
                value={vendorGstin}
                onChange={(e) => setVendorGstin(e.target.value.toUpperCase())}
                placeholder="e.g. 32AABCU9603R1ZX"
                maxLength={15}
              />
            </FieldWrapper>

            <TaxBreakdownGroup
              taxableAmount={taxableAmount}
              cgstAmount={cgstAmount}
              sgstAmount={sgstAmount}
              igstAmount={igstAmount}
              onChangeTaxable={setTaxableAmount}
              onChangeCgst={setCgstAmount}
              onChangeSgst={setSgstAmount}
              onChangeIgst={setIgstAmount}
            />

            <FieldWrapper label="Notes (optional)">
              <textarea
                className={`${inputClass} h-20 py-3 resize-none`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any additional notes…"
              />
            </FieldWrapper>
          </div>
        )}
      </div>

      {/* Sticky CTA */}
      <StickyFooter>
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full h-14 rounded-2xl text-white font-semibold text-base flex flex-col items-center justify-center gap-0.5 disabled:opacity-60 transition-opacity"
          style={{ background: "var(--color-aubergine)" }}
        >
          <span>✓ Looks good!</span>
          <span className="text-xs font-normal opacity-80">ശരി</span>
        </button>
      </StickyFooter>

      {/* Pickers */}
      <CategoryPicker
        value={category}
        onChange={setCategory}
        open={catOpen}
        onClose={() => setCatOpen(false)}
      />
      <DatePicker
        value={billDate}
        onChange={setBillDate}
        open={dateOpen}
        onClose={() => setDateOpen(false)}
      />
    </main>
  );
}

export default function ReviewPage({
  params,
}: {
  params: Promise<{ bill_id: string }>;
}) {
  const { bill_id } = use(params);
  return (
    <Suspense fallback={<div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">Loading…</div>}>
      <ReviewContent bill_id={bill_id} />
    </Suspense>
  );
}
