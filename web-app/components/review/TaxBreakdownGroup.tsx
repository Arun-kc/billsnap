"use client";

interface TaxBreakdownGroupProps {
  taxableAmount?: number;
  cgstAmount: number;
  sgstAmount: number;
  igstAmount: number;
  onChangeTaxable: (v: number) => void;
  onChangeCgst: (v: number) => void;
  onChangeSgst: (v: number) => void;
  onChangeIgst: (v: number) => void;
}

function NumInput({
  label,
  value,
  onChange,
  muted = false,
  className = "",
}: {
  label: string;
  value?: number;
  onChange: (v: number) => void;
  muted?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label className="text-xs font-medium text-[var(--color-text-muted)]">{label}</label>
      <input
        type="number"
        inputMode="decimal"
        step="0.01"
        value={value ?? ""}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className={`h-12 rounded-xl border border-[var(--color-border)] px-3 text-base bg-white focus:outline-none focus:border-[var(--color-aubergine)] ${muted ? "text-[var(--color-text-muted)]" : "text-[var(--color-text)]"}`}
      />
    </div>
  );
}

export default function TaxBreakdownGroup({
  taxableAmount,
  cgstAmount,
  sgstAmount,
  igstAmount,
  onChangeTaxable,
  onChangeCgst,
  onChangeSgst,
  onChangeIgst,
}: TaxBreakdownGroupProps) {
  const gstRate =
    taxableAmount && taxableAmount > 0
      ? (((cgstAmount ?? 0) + (sgstAmount ?? 0)) / taxableAmount) * 100
      : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3 text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">
        <div className="flex-1 h-px bg-[var(--color-border)]" />
        Tax Breakdown
        <div className="flex-1 h-px bg-[var(--color-border)]" />
      </div>

      <NumInput
        label="Taxable Amount (₹)"
        value={taxableAmount}
        onChange={onChangeTaxable}
      />

      {/* CGST + SGST side by side */}
      <div className="grid grid-cols-2 gap-3">
        <NumInput label="CGST (₹)" value={cgstAmount} onChange={onChangeCgst} />
        <NumInput label="SGST (₹)" value={sgstAmount} onChange={onChangeSgst} />
      </div>

      {/* GST Rate — computed, read-only */}
      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-[var(--color-text-muted)]">GST Rate</span>
        <p className="text-base text-[var(--color-text-muted)] px-1">
          {gstRate != null ? `${gstRate.toFixed(0)}% (computed)` : "—"}
        </p>
      </div>

      <NumInput
        label="IGST Amount (₹)"
        value={igstAmount}
        onChange={onChangeIgst}
        muted
      />
    </div>
  );
}
