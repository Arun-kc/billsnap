"use client";

import { useEffect } from "react";

export type ToastVariant = "success" | "error";

interface ToastProps {
  message: string;
  variant?: ToastVariant;
  onDismiss: () => void;
  durationMs?: number;
}

export default function Toast({
  message,
  variant = "success",
  onDismiss,
  durationMs = 4000,
}: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(timer);
  }, [onDismiss, durationMs]);

  const isError = variant === "error";
  const bg = isError ? "var(--color-warning-bg)" : "#ecfdf5";
  const fg = isError ? "var(--color-warning)" : "#047857";
  const border = isError ? "var(--color-warning)" : "#10b981";

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-live="polite"
      className="fixed left-1/2 -translate-x-1/2 bottom-24 z-50 animate-slide-up w-[min(92vw,420px)]"
    >
      <button
        type="button"
        onClick={onDismiss}
        className="w-full flex items-start gap-3 rounded-2xl px-4 py-3 text-left shadow-lg border"
        style={{ background: bg, color: fg, borderColor: border }}
      >
        <span className="flex-1 text-sm font-medium leading-snug">{message}</span>
        <span aria-hidden="true" className="text-lg leading-none opacity-60">
          ×
        </span>
      </button>
    </div>
  );
}
