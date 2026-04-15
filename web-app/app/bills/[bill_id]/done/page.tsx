"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getBill, type BillDetail } from "@/lib/api";
import { formatCurrency } from "@/lib/currency";

function isLastWeekOfMonth(): boolean {
  const now = new Date();
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  return now.getDate() >= lastDay - 6;
}

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function DonePage({
  params,
}: {
  params: Promise<{ bill_id: string }>;
}) {
  const { bill_id } = use(params);
  const router = useRouter();
  const [bill, setBill] = useState<BillDetail | null>(null);

  useEffect(() => {
    getBill(bill_id).then(setBill).catch(() => null);
  }, [bill_id]);

  const vendorName = bill?.vendor_name ?? "your vendor";
  const amount = bill?.total_amount;
  const dateStr = bill?.bill_date
    ? new Date(bill.bill_date + "T00:00:00").toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-[var(--color-surface)] px-6 gap-8">
      {/* Step indicator */}
      <span className="absolute top-5 right-5 text-sm font-medium text-[var(--color-text-muted)]">
        Step 3 / 3
      </span>

      {/* Animated checkmark */}
      <div
        className="text-7xl"
        style={{ animation: "checkPop 300ms cubic-bezier(0.34, 1.56, 0.64, 1) both" }}
      >
        ✅
      </div>

      {/* Summary */}
      <div className="text-center flex flex-col gap-2">
        <h1
          className="font-bold text-[var(--color-text)]"
          style={{ fontSize: "var(--text-2xl)" }}
        >
          Bill saved!
        </h1>
        {amount != null && (
          <p
            className="text-[var(--color-text-secondary)]"
            style={{ fontSize: "var(--text-lg)" }}
          >
            {formatCurrency(amount)} from{" "}
            <span className="font-semibold text-[var(--color-text)]">{vendorName}</span>
          </p>
        )}
        {dateStr && (
          <p className="text-sm text-[var(--color-text-muted)]">{dateStr}</p>
        )}
      </div>

      {/* CTAs */}
      <div className="w-full max-w-xs flex flex-col gap-3">
        <button
          onClick={() => router.push("/upload")}
          className="w-full h-14 rounded-2xl text-white font-semibold text-base flex flex-col items-center justify-center gap-0.5"
          style={{ background: "var(--color-aubergine)" }}
        >
          <span>📷 Add another bill</span>
          <span className="text-xs font-normal opacity-80">വേറൊന്ന് ചേർക്കൂ</span>
        </button>

        <Link
          href="/bills"
          className="w-full h-11 flex items-center justify-center text-sm font-medium text-[var(--color-aubergine)]"
        >
          View all bills
        </Link>

        {isLastWeekOfMonth() && (
          <Link
            href={`/bills?export=${currentMonth()}`}
            className="w-full h-11 flex items-center justify-center text-sm font-medium text-[var(--color-text-muted)]"
          >
            Export this month
          </Link>
        )}
      </div>

      <style>{`
        @keyframes checkPop {
          from { transform: scale(0); opacity: 0; }
          to   { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </main>
  );
}
