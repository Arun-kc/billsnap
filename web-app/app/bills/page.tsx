"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { listBills, exportUrl, type BillSummary, type MonthlySummary } from "@/lib/api";
import { formatCurrency } from "@/lib/currency";
import BillCard from "@/components/bills/BillCard";
import MonthSwitcher from "@/components/bills/MonthSwitcher";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function BillsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [month, setMonth] = useState<string>(
    searchParams.get("month") ?? currentMonth()
  );
  const [bills, setBills] = useState<BillSummary[]>([]);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const PER_PAGE = 20;

  const fetchBills = useCallback(
    async (m: string, p: number, append = false) => {
      try {
        const res = await listBills({ month: m, page: p, per_page: PER_PAGE });
        if (append) {
          setBills((prev) => [...prev, ...res.bills]);
        } else {
          setBills(res.bills);
          setSummary(res.summary);
          setTotal(res.pagination.total);
        }
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    []
  );

  useEffect(() => {
    setLoading(true);
    setPage(1);
    fetchBills(month, 1);
  }, [month, fetchBills]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    setLoadingMore(true);
    fetchBills(month, nextPage, true);
  };

  const handleExport = () => {
    const url = exportUrl(month, "xlsx");
    window.open(url, "_blank");
  };

  const hasMore = bills.length < total;
  const hasBills = bills.length > 0 || (summary?.bill_count ?? 0) > 0;

  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-surface)] pb-28">
      {/* ── Sticky header ── */}
      <header className="sticky top-0 z-30" style={{ background: "var(--color-aubergine)" }}>
        {/* Brand bar */}
        <div className="flex items-center justify-between px-5 pt-safe-top py-3.5">
          <div className="flex items-center gap-2">
            {/* Snap Bill icon (inline SVG) */}
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
              <rect x="5" y="2" width="14" height="19" rx="2" fill="white" opacity="0.9" transform="rotate(-8 5 2)"/>
              <rect x="5" y="2" width="14" height="19" rx="2" fill="none" stroke="white" strokeWidth="1" strokeOpacity="0.4" transform="rotate(-8 5 2)"/>
              <rect x="9" y="4" width="14" height="19" rx="2" fill="#C9A227" opacity="0.25"/>
              <polygon points="18,6 22,14 19,14 21,22 16,13 19,13" fill="#C9A227"/>
            </svg>
            <span
              className="font-bold text-white leading-none"
              style={{ fontSize: "var(--text-xl)", fontFamily: "var(--font-urbanist)" }}
            >
              BillSnap
            </span>
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-1.5 text-sm font-medium text-white min-h-[44px] px-3 py-1 rounded-xl"
            style={{ background: "rgba(255,255,255,0.15)" }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M7 1v8M4 6l3 3 3-3M2 10v1a1 1 0 001 1h8a1 1 0 001-1v-1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Export
          </button>
        </div>

        {/* Month switcher — on white pill at bottom of header */}
        <div className="px-4 pb-3">
          <div
            className="rounded-xl overflow-hidden"
            style={{ background: "rgba(255,255,255,0.12)" }}
          >
            <MonthSwitcher value={month} onChange={setMonth} dark />
          </div>
        </div>
      </header>

      {/* ── Summary strip ── */}
      {hasBills && summary && (
        <div className="grid grid-cols-3 px-5 pt-4 pb-3 gap-3">
          <div className="flex flex-col gap-0.5 p-3 rounded-2xl bg-white border border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-muted)] font-medium">Total spent</span>
            <span
              className="font-bold text-[var(--color-aubergine)]"
              style={{ fontSize: "var(--text-lg)", fontFamily: "var(--font-urbanist)" }}
            >
              {formatCurrency(summary.total_amount)}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 p-3 rounded-2xl bg-white border border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-muted)] font-medium">Bills</span>
            <span
              className="font-bold text-[var(--color-text)]"
              style={{ fontSize: "var(--text-lg)", fontFamily: "var(--font-urbanist)" }}
            >
              {summary.bill_count}
            </span>
          </div>
          <div className="flex flex-col gap-0.5 p-3 rounded-2xl bg-white border border-[var(--color-border)]">
            <span className="text-xs text-[var(--color-text-muted)] font-medium">
              {summary.unverified_count > 0 ? "Need review" : "All verified"}
            </span>
            <span
              className="font-bold"
              style={{
                fontSize: "var(--text-lg)",
                fontFamily: "var(--font-urbanist)",
                color: summary.unverified_count > 0
                  ? "var(--color-warning)"
                  : "var(--color-success)",
              }}
            >
              {summary.unverified_count > 0 ? summary.unverified_count : "✓"}
            </span>
          </div>
        </div>
      )}

      {/* ── Bills list ── */}
      <div className="flex flex-col gap-2 px-5 pt-1">
        {loading ? (
          /* Skeleton */
          <div className="flex flex-col gap-2 pt-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 rounded-2xl bg-white border border-[var(--color-border)] animate-pulse"
              />
            ))}
          </div>
        ) : bills.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 gap-5 text-center">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center text-4xl"
              style={{ background: "var(--color-surface-2)" }}
            >
              🧾
            </div>
            <div className="flex flex-col gap-1.5">
              <p
                className="font-bold text-[var(--color-text)]"
                style={{ fontSize: "var(--text-xl)", fontFamily: "var(--font-urbanist)" }}
              >
                No bills this month
              </p>
              <p className="text-sm text-[var(--color-text-muted)]">
                Snap your first one to get started!
              </p>
            </div>
            <Link
              href="/upload"
              className="h-12 px-8 rounded-2xl text-white font-semibold text-sm flex items-center gap-2"
              style={{ background: "var(--color-aubergine)" }}
            >
              📷 Add a bill
            </Link>
          </div>
        ) : (
          <>
            {bills.map((bill) => (
              <BillCard key={bill.id} bill={bill} />
            ))}

            {hasMore && (
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="mt-2 h-11 w-full rounded-xl border border-[var(--color-border)] text-sm font-medium text-[var(--color-text-secondary)] disabled:opacity-50"
              >
                {loadingMore ? "Loading…" : `Load more (${total - bills.length} remaining)`}
              </button>
            )}
          </>
        )}
      </div>

      {/* ── FAB ── */}
      <button
        onClick={() => router.push("/upload")}
        className="fixed bottom-6 right-5 z-40 h-14 px-5 rounded-full shadow-xl text-white font-semibold text-sm flex items-center gap-2"
        style={{ background: "var(--color-aubergine)" }}
        aria-label="Upload a bill"
      >
        <span className="text-lg leading-none">+</span>
        <span>Add bill</span>
      </button>
    </main>
  );
}

export default function BillsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">
        Loading…
      </div>
    }>
      <BillsContent />
    </Suspense>
  );
}
