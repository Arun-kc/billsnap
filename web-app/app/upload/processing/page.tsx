"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getJobStatus } from "@/lib/api";
import ProgressBar from "@/components/ui/ProgressBar";

const POLL_INTERVAL_MS = 2000;
const LONG_WAIT_THRESHOLD_MS = 30000;

function ProcessingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id") ?? "";

  const [statusText, setStatusText] = useState("Reading your bill...");
  const [cancelled, setCancelled] = useState(false);
  const startedAt = useRef(Date.now());
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId || cancelled) return;

    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);

        if (status.status === "completed" || status.status === "needs_review") {
          clearInterval(pollRef.current!);
          router.replace(`/bills/${status.bill_id}/review`);
          return;
        }

        if (status.status === "failed") {
          clearInterval(pollRef.current!);
          router.replace(`/bills/new/review?error=ocr_failed`);
          return;
        }

        const elapsed = Date.now() - startedAt.current;
        if (elapsed > LONG_WAIT_THRESHOLD_MS) {
          setStatusText("Still working, almost there...");
        }
      } catch {
        // Network error — keep polling
      }
    };

    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId, cancelled, router]);

  const handleCancel = () => {
    setCancelled(true);
    if (pollRef.current) clearInterval(pollRef.current);
    router.replace("/upload");
  };

  return (
    <main className="min-h-dvh flex flex-col items-center justify-center bg-[var(--color-surface)] px-8 gap-8">
      {/* Step indicator */}
      <span className="absolute top-5 right-5 text-sm font-medium text-[var(--color-text-muted)]">
        Step 2 / 3
      </span>

      {/* Icon */}
      <div className="text-6xl animate-pulse-dot">🔍</div>

      {/* Status */}
      <div className="text-center flex flex-col gap-2">
        <p
          className="font-semibold text-[var(--color-text)]"
          style={{ fontSize: "var(--text-xl)" }}
        >
          {statusText}
        </p>
        <p className="text-sm text-[var(--color-text-muted)]">
          This takes about 10–15 seconds
        </p>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-xs">
        <ProgressBar fakeDuration={15000} />
      </div>

      {/* Cancel */}
      <button
        onClick={handleCancel}
        className="text-sm text-[var(--color-text-muted)] underline underline-offset-2 min-h-[44px] px-4"
      >
        Cancel
      </button>
    </main>
  );
}

export default function ProcessingPage() {
  return (
    <Suspense fallback={<div className="min-h-dvh flex items-center justify-center text-[var(--color-text-muted)]">Loading…</div>}>
      <ProcessingContent />
    </Suspense>
  );
}
