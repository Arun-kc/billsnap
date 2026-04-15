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

interface BillCardProps {
  bill: BillSummary;
}

export default function BillCard({ bill }: BillCardProps) {
  return (
    <Link
      href={`/bills/${bill.id}/review`}
      className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-[var(--color-border)] hover:border-[var(--color-aubergine-light)] transition-colors active:scale-[0.98] transition-transform"
    >
      {/* Thumbnail */}
      <div className="relative w-[52px] h-[68px] rounded-lg overflow-hidden flex-shrink-0 bg-[var(--color-surface-2)]">
        {bill.thumbnail_url ? (
          <Image
            src={bill.thumbnail_url}
            alt=""
            fill
            className="object-cover"
            sizes="52px"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-2xl text-[var(--color-text-muted)]">
            🧾
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col flex-1 gap-0.5 min-w-0">
        <p className="text-sm font-semibold text-[var(--color-text)] truncate">
          {bill.vendor_name ?? "Unknown Vendor"}
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          {formatDate(bill.bill_date)}
          {bill.category && ` · ${bill.category}`}
        </p>
        <p
          className="font-bold text-[var(--color-text)] mt-0.5"
          style={{ fontSize: "var(--text-lg)" }}
        >
          {formatCurrency(bill.total_amount)}
        </p>
      </div>

      {/* Verified badge */}
      <div className="flex-shrink-0 flex flex-col items-center gap-1">
        {bill.is_verified ? (
          <span className="text-[var(--color-success)] text-lg">✓</span>
        ) : (
          <span
            className="w-2.5 h-2.5 rounded-full"
            style={{ background: "var(--color-warning)" }}
            title="Needs review"
          />
        )}
      </div>
    </Link>
  );
}
