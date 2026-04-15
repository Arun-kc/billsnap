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

  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-surface)] pb-24">
      {/* Header */}
      <header className="bg-white border-b border-[var(--color-border)] sticky top-0 z-30">
        <div className="flex items-center justify-between px-5 py-4">
          <h1
            className="font-bold text-[var(--color-text)]"
            style={{ fontSize: "var(--text-xl)", fontFamily: "var(--font-urbanist)" }}
          >
            BillSnap
          </h1>
          <button
            onClick={handleExport}
            className="text-sm font-medium text-[var(--color-aubergine)] min-h-[44px] px-2"
          >
            Export ↓
          </button>
        </div>

        <MonthSwitcher value={month} onChange={setMonth} />
      </header>

      {/* Summary strip */}
      {summary && summary.bill_count > 0 && (
        <div className="flex gap-3 px-5 py-4 bg-[var(--color-surface-2)] border-b border-[var(--color-border)]">
          <div className="flex flex-col flex-1">
            <span className="text-xs text-[var(--color-text-muted)]">Total spent</span>
            <span className="text-base font-bold text-[var(--color-text)]">
              {formatCurrency(summary.total_amount)}
            </span>
          </div>
          <div className="flex flex-col flex-1">
            <span className="text-xs text-[var(--color-text-muted)]">Bills</span>
            <span className="text-base font-bold text-[var(--color-text)]">
              {summary.bill_count}
            </span>
          </div>
          {summary.unverified_count > 0 && (
            <div className="flex flex-col flex-1">
              <span className="text-xs text-[var(--color-text-muted)]">Needs review</span>
              <span
                className="text-base font-bold"
                style={{ color: "var(--color-warning)" }}
              >
                {summary.unverified_count}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Bills list */}
      <div className="flex flex-col gap-3 px-5 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-[var(--color-text-muted)]">
            Loading bills…
          </div>
        ) : bills.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-16 gap-5 text-center">
            <div className="text-5xl">🧾</div>
            <div className="flex flex-col gap-1.5">
              <p className="font-semibold text-[var(--color-text)]">No bills yet</p>
              <p className="text-sm text-[var(--color-text-muted)]">
                Snap your first one to get started!
              </p>
            </div>
            <Link
              href="/upload"
              className="h-12 px-6 rounded-xl text-white font-semibold text-sm flex items-center"
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
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            )}
          </>
        )}
      </div>

      {/* FAB — Upload */}
      <button
        onClick={() => router.push("/upload")}
        className="fixed bottom-6 right-5 z-40 w-14 h-14 rounded-full shadow-lg text-white text-2xl flex items-center justify-center"
        style={{ background: "var(--color-aubergine)" }}
        aria-label="Upload a bill"
      >
        +
      </button>
    </main>
  );
}

export default function BillsPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">Loading…</div>}>
      <BillsContent />
    </Suspense>
  );
}
