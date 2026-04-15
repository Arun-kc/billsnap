"use client";

import { useEffect, useState } from "react";

interface ProgressBarProps {
  /** If provided, shows exact progress. Otherwise animates fake progress. */
  value?: number;
  /** Duration in ms for the fake progress animation to reach ~90% */
  fakeDuration?: number;
}

export default function ProgressBar({
  value,
  fakeDuration = 15000,
}: ProgressBarProps) {
  const [fakeProgress, setFakeProgress] = useState(0);

  useEffect(() => {
    if (value !== undefined) return;

    // Animate from 0 → 90 over fakeDuration, then hold
    const start = performance.now();
    let raf: number;

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(90, (elapsed / fakeDuration) * 90);
      setFakeProgress(progress);
      if (progress < 90) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, fakeDuration]);

  const pct = value !== undefined ? value : fakeProgress;

  return (
    <div
      className="w-full h-2.5 bg-[var(--color-surface-2)] rounded-full overflow-hidden"
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{
          width: `${pct}%`,
          background:
            "linear-gradient(90deg, var(--color-aubergine), var(--color-aubergine-light))",
        }}
      />
    </div>
  );
}
