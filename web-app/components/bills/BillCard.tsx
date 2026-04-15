import Link from "next/link";
import Image from "next/image";
import type { BillSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/currency";

function formatDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  electrical:  { bg: "#EDE9FE", text: "#5C2D91" },
  materials:   { bg: "#FEF3C7", text: "#92400E" },
  groceries:   { bg: "#DCFCE7", text: "#166534" },
  services:    { bg: "#DBEAFE", text: "#1E40AF" },
  utilities:   { bg: "#E0F2FE", text: "#075985" },
  medical:     { bg: "#FCE7F3", text: "#9D174D" },
  transport:   { bg: "#F3F4F6", text: "#374151" },
  other:       { bg: "#F3F4F6", text: "#374151" },
};

function CategoryBadge({ category }: { category?: string | null }) {
  if (!category) return null;
  const style = CATEGORY_COLORS[category] ?? CATEGORY_COLORS.other;
  const label = category.charAt(0).toUpperCase() + category.slice(1);
  return (
    <span
      className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
      style={{ background: style.bg, color: style.text }}
    >
      {label}
    </span>
  );
}

interface BillCardProps {
  bill: BillSummary;
}

export default function BillCard({ bill }: BillCardProps) {
  return (
    <Link
      href={`/bills/${bill.id}/review`}
      className="flex gap-3 p-4 bg-white rounded-2xl border active:scale-[0.98] transition-all"
      style={{ borderColor: bill.is_verified ? "var(--color-border)" : "var(--color-warning)" }}
    >
      {/* Thumbnail */}
      <div className="relative w-[48px] h-[64px] rounded-xl overflow-hidden flex-shrink-0 bg-[var(--color-surface-2)]">
        {bill.thumbnail_url ? (
          <Image
            src={bill.thumbnail_url}
            alt=""
            fill
            className="object-cover"
            sizes="48px"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-xl text-[var(--color-text-muted)]">
            🧾
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col flex-1 gap-1.5 min-w-0 justify-center">
        {/* Top row: vendor + amount */}
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-[var(--color-text)] truncate leading-tight" style={{ fontSize: "var(--text-base)" }}>
            {bill.vendor_name ?? "Unknown Vendor"}
          </p>
          <p
            className="font-bold text-[var(--color-text)] flex-shrink-0"
            style={{ fontSize: "var(--text-lg)", fontFamily: "var(--font-urbanist)" }}
          >
            {formatCurrency(bill.total_amount)}
          </p>
        </div>

        {/* Bottom row: date + category + status */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-[var(--color-text-muted)]">
            {formatDate(bill.bill_date)}
          </span>
          {bill.category && <CategoryBadge category={bill.category} />}
          {!bill.is_verified && (
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full"
              style={{ background: "var(--color-warning-bg)", color: "var(--color-warning)" }}
            >
              Review needed
            </span>
          )}
        </div>
      </div>

      {/* Right arrow */}
      <div className="flex items-center flex-shrink-0 text-[var(--color-text-muted)] self-center">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
    </Link>
  );
}
