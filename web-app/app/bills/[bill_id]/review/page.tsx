"use client";

import { useEffect, useState, use, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getBill, updateBill, type BillDetail } from "@/lib/api";
import { formatAmount, parseAmount } from "@/lib/currency";
import CategoryPicker from "@/components/review/CategoryPicker";
import DatePicker, { formatForDisplay } from "@/components/review/DatePicker";
import TaxBreakdownGroup from "@/components/review/TaxBreakdownGroup";
import ImagePeekButton from "@/components/review/ImagePeekButton";
import LineItemsSection from "@/components/review/LineItemsSection";
import LineItemsEditor, { type DraftLineItem } from "@/components/review/LineItemsEditor";
import { labels } from "@/lib/i18n/labels";
import StickyFooter from "@/components/ui/StickyFooter";
import Toast, { type ToastVariant } from "@/components/ui/Toast";

const DOCUMENT_TYPES = [
  { value: "tax_invoice", label: "Tax Invoice" },
  { value: "bill_of_supply", label: "Bill of Supply" },
  { value: "receipt", label: "Receipt" },
  { value: "credit_note", label: "Credit Note" },
  { value: "debit_note", label: "Debit Note" },
  { value: "other", label: "Other" },
];

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="text-xs font-semibold uppercase tracking-widest"
      style={{ color: "var(--color-text-muted)" }}
    >
      {children}
    </p>
  );
}

function Field({
  label,
  ml,
  lowConfidence = false,
  children,
}: {
  label: string;
  ml?: string;
  lowConfidence?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`flex flex-col gap-1.5 ${
        lowConfidence
          ? "rounded-2xl ring-2 ring-[var(--color-gold)] ring-opacity-60 p-2 -m-2 bg-[var(--color-gold-bg,#fffbeb)]"
          : ""
      }`}
    >
      <label className="flex items-center gap-1.5 text-xs font-medium text-[var(--color-text-muted)]">
        <span>{label}</span>
        {ml && (
          <span
            className="text-[11px] font-normal opacity-70"
            lang="ml"
            style={{ fontFamily: "'Noto Sans Malayalam', sans-serif" }}
          >
            · {ml}
          </span>
        )}
        {lowConfidence && (
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded-full"
            style={{ background: "var(--color-warning-bg)", color: "var(--color-warning)" }}
            title="We're not sure — please check"
          >
            Check this
          </span>
        )}
      </label>
      {children}
    </div>
  );
}

const inputBase =
  "w-full h-12 rounded-xl border border-[var(--color-border)] px-4 bg-white text-[var(--color-text)] focus:outline-none focus:ring-2 transition-all";
const inputFocusRing = "focus:ring-[var(--color-aubergine)] focus:ring-opacity-30 focus:border-[var(--color-aubergine)]";
const inputClass = `${inputBase} ${inputFocusRing}`;

function ReviewContent({ bill_id }: { bill_id: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const ocrFailed = searchParams.get("error") === "ocr_failed";

  const [bill, setBill] = useState<BillDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null);
  const [showMore, setShowMore] = useState(false);
  const [catOpen, setCatOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const [itemsOpen, setItemsOpen] = useState(false);
  const [lineItems, setLineItems] = useState<DraftLineItem[]>([]);
  const [lineItemsDirty, setLineItemsDirty] = useState(false);

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
        setLineItems(
          (b.line_items ?? []).map((li) => ({
            item_name: li.item_name,
            quantity: li.quantity,
            unit_price: li.unit_price,
            total_price: li.total_price,
          }))
        );
      })
      .catch(() => {/* treat as blank */})
      .finally(() => setLoading(false));
  }, [bill_id]);

  const lowConfidenceOverall =
    typeof bill?.extraction_confidence === "number" && bill.extraction_confidence < 0.70;

  const isLowConf = (field: string) => {
    if (!lowConfidenceOverall) return false;
    return ["vendor_name", "total_amount", "vendor_gstin", "bill_date"].includes(field);
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
          ...(lineItemsDirty
            ? {
                line_items: lineItems.map((li, i) => ({
                  item_name: li.item_name,
                  quantity: li.quantity,
                  unit_price: li.unit_price,
                  total_price: li.total_price,
                  sort_order: i,
                })),
              }
            : {}),
        });
        router.replace(`/bills/${bill_id}/done`);
      }
    } catch {
      setSaving(false);
      setToast({
        message: "Couldn't save. Tap ശരി to try again.",
        variant: "error",
      });
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
      {/* ── Top bar ── */}
      <header
        className="flex items-center justify-between px-5 pt-safe-top py-3.5"
        style={{ background: "var(--color-aubergine)" }}
      >
        <button
          onClick={() => router.back()}
          className="text-white text-sm font-medium min-w-[44px] min-h-[44px] flex items-center gap-1 opacity-80"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back
        </button>
        <span
          className="text-sm font-semibold text-white"
          style={{ fontFamily: "var(--font-urbanist)" }}
        >
          Review Bill
        </span>
        <span className="text-xs text-white opacity-60 min-w-[44px] text-right">2 / 3</span>
      </header>

      <div className="flex flex-col gap-5 px-5 pt-5 pb-36">
        {/* OCR failed notice */}
        {ocrFailed && (
          <div
            className="rounded-2xl p-4 text-sm flex gap-3 items-start"
            style={{ background: "var(--color-info-bg)", color: "var(--color-info)" }}
          >
            <span className="text-lg leading-none mt-0.5">ℹ️</span>
            <p>We couldn&apos;t read this bill clearly. Please fill in the details below.</p>
          </div>
        )}

        {/* Low-confidence guidance */}
        {!ocrFailed && lowConfidenceOverall && (
          <div
            className="rounded-2xl p-4 text-sm flex gap-3 items-start border"
            style={{
              background: "var(--color-gold-bg, #fffbeb)",
              borderColor: "var(--color-gold)",
              color: "#7a5a00",
            }}
          >
            <span className="text-lg leading-none mt-0.5" aria-hidden="true">💡</span>
            <p>
              We weren&apos;t sure about a few things. Please double-check the highlighted boxes below.
            </p>
          </div>
        )}

        {/* ── Primary fields ── */}
        <div className="flex flex-col gap-4">
          <SectionLabel>Key details</SectionLabel>

          <Field label={labels.vendor.en} ml={labels.vendor.ml} lowConfidence={isLowConf("vendor_name")}>
            <input
              type="text"
              className={inputClass}
              style={{ fontSize: "var(--text-base)", fontFamily: "var(--font-urbanist)", fontWeight: 600 }}
              value={vendorName}
              onChange={(e) => setVendorName(e.target.value)}
              placeholder="e.g. Sharma Electricals"
            />
          </Field>

          <Field label={labels.billNumber.en} ml={labels.billNumber.ml}>
            <input
              type="text"
              className={inputClass}
              value={billNumber}
              onChange={(e) => setBillNumber(e.target.value)}
              placeholder="e.g. INV-2026-042"
            />
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label={labels.date.en} ml={labels.date.ml} lowConfidence={isLowConf("bill_date")}>
              <button
                type="button"
                onClick={() => setDateOpen(true)}
                className={`${inputClass} flex items-center justify-between text-left`}
                style={{ fontSize: "var(--text-sm)" }}
              >
                <span className={billDate ? "text-[var(--color-text)]" : "text-[var(--color-text-muted)]"}>
                  {billDate ? formatForDisplay(billDate) : "Pick date"}
                </span>
                <span className="text-base">📅</span>
              </button>
            </Field>

            <Field label={labels.docType.en} ml={labels.docType.ml}>
              <select
                className={inputClass}
                style={{ fontSize: "var(--text-sm)" }}
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
              >
                {DOCUMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label={labels.category.en} ml={labels.category.ml}>
            <button
              type="button"
              onClick={() => setCatOpen(true)}
              className={`${inputClass} flex items-center justify-between text-left`}
              style={{ fontSize: "var(--text-sm)" }}
            >
              <span className={category ? "text-[var(--color-text)]" : "text-[var(--color-text-muted)]"}>
                {category ? category.charAt(0).toUpperCase() + category.slice(1) : "Category"}
              </span>
              <span className="text-[var(--color-text-muted)] text-xs">▼</span>
            </button>
          </Field>

          <Field label={labels.total.en} ml={labels.total.ml} lowConfidence={isLowConf("total_amount")}>
            <div className="relative">
              <span
                className="absolute left-4 top-1/2 -translate-y-1/2 font-bold text-[var(--color-text-muted)]"
                style={{ fontSize: "var(--text-lg)" }}
              >
                ₹
              </span>
              <input
                type="text"
                inputMode="decimal"
                className={`${inputClass} pl-8 font-bold`}
                style={{ fontSize: "1.5rem" }}
                value={totalAmount !== undefined ? formatAmount(totalAmount) : ""}
                onChange={(e) => setTotalAmount(parseAmount(e.target.value))}
                placeholder="0.00"
              />
            </div>
          </Field>
        </div>

        {/* ── Line items ── */}
        <LineItemsSection items={lineItems} onEdit={() => setItemsOpen(true)} />

        {/* ── More details (collapsible) ── */}
        <div
          className="rounded-2xl overflow-hidden border border-[var(--color-border)] bg-white"
        >
          <button
            type="button"
            onClick={() => setShowMore((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3.5 text-sm font-semibold text-[var(--color-aubergine)] min-h-[44px]"
          >
            <span>More details (GSTIN, taxes, notes)</span>
            <span className="text-xs">{showMore ? "▲" : "▼"}</span>
          </button>

          {showMore && (
            <div className="flex flex-col gap-4 px-4 pb-4 pt-1 animate-slide-up border-t border-[var(--color-border)]">
              <Field label={labels.gstin.en} ml={labels.gstin.ml} lowConfidence={isLowConf("vendor_gstin")}>
                <input
                  type="text"
                  className={`${inputClass} uppercase tracking-widest`}
                  style={{ fontSize: "var(--text-sm)", letterSpacing: "0.08em" }}
                  value={vendorGstin}
                  onChange={(e) => setVendorGstin(e.target.value.toUpperCase())}
                  placeholder="e.g. 32AABCU9603R1ZX"
                  maxLength={15}
                />
              </Field>

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

              <Field label={labels.notes.en} ml={labels.notes.ml}>
                <textarea
                  className={`${inputClass} h-20 py-3 resize-none`}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any additional notes…"
                />
              </Field>
            </div>
          )}
        </div>
      </div>

      {/* ── Floating image peek ── */}
      <ImagePeekButton
        thumbnailUrl={bill?.thumbnail_url}
        imageUrl={bill?.image_url}
      />

      {/* ── Sticky CTA ── */}
      <StickyFooter>
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full h-14 rounded-2xl text-white font-bold text-base flex items-center justify-center gap-2 disabled:opacity-60 transition-opacity"
          style={{ background: "var(--color-aubergine)", fontFamily: "var(--font-urbanist)" }}
        >
          {saving ? (
            <span>Saving…</span>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M4 10l4 4 8-8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>Confirm &amp; Save</span>
              <span className="text-sm font-normal opacity-70 ml-1">ശരി</span>
            </>
          )}
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
      <LineItemsEditor
        open={itemsOpen}
        onClose={() => setItemsOpen(false)}
        initialItems={lineItems}
        onSave={(next) => {
          setLineItems(next);
          setLineItemsDirty(true);
        }}
      />

      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}
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
    <Suspense fallback={
      <div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">
        Loading…
      </div>
    }>
      <ReviewContent bill_id={bill_id} />
    </Suspense>
  );
}
