"use client";

import { useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { uploadBill } from "@/lib/api";

type UploadState = "idle" | "captured" | "uploading" | "error";

const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileSelect = useCallback((f: File) => {
    if (!f.type.startsWith("image/")) {
      if (f.type === "application/pdf") {
        setErrorMsg("PDF upload is coming soon! Please use a photo for now.");
      } else {
        setErrorMsg("Only photo files (JPEG, PNG) are supported.");
      }
      return;
    }
    if (f.size > MAX_FILE_BYTES) {
      setErrorMsg("Photo too large (max 10 MB). Try lowering your camera resolution.");
      return;
    }
    setErrorMsg(null);
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url);
    setState("captured");
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFileSelect(f);
    e.target.value = "";
  };

  const handleRetake = () => {
    setPreview(null);
    setFile(null);
    setState("idle");
    setErrorMsg(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setState("uploading");
    try {
      const res = await uploadBill(file);
      router.push(`/upload/processing?job_id=${res.job_id}`);
    } catch {
      setState("error");
      setErrorMsg("Couldn't upload. Check your connection and try again.");
    }
  };

  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      {/* ── Header ── */}
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
          Add Bill
        </span>
        <span className="text-xs text-white opacity-60 min-w-[44px] text-right">1 / 3</span>
      </header>

      <div className="flex flex-col flex-1 px-5 pt-6 pb-40 gap-4">
        {/* Error banner */}
        {errorMsg && (
          <div
            className="rounded-2xl p-4 text-sm flex gap-3 items-start"
            style={{ background: "var(--color-warning-bg)", color: "var(--color-warning)" }}
          >
            <span className="text-lg leading-none mt-0.5">⚠️</span>
            <p>{errorMsg}</p>
          </div>
        )}

        {state === "idle" ? (
          /* ── Idle state: camera-first UI ── */
          <>
            {/* Hero illustration */}
            <div
              className="w-full rounded-3xl flex flex-col items-center justify-center gap-4 py-12"
              style={{ background: "var(--color-surface-2)" }}
            >
              {/* Stylised receipt icon */}
              <svg width="72" height="88" viewBox="0 0 72 88" fill="none" aria-hidden="true">
                <rect x="8" y="4" width="48" height="64" rx="4" fill="white" stroke="var(--color-border-strong)" strokeWidth="1.5"/>
                <line x1="18" y1="18" x2="48" y2="18" stroke="var(--color-border-strong)" strokeWidth="1.5"/>
                <line x1="18" y1="26" x2="48" y2="26" stroke="var(--color-border-strong)" strokeWidth="1.5"/>
                <line x1="18" y1="34" x2="36" y2="34" stroke="var(--color-border-strong)" strokeWidth="1.5"/>
                <line x1="18" y1="50" x2="48" y2="50" stroke="var(--color-border-strong)" strokeWidth="2"/>
                {/* Gold lightning bolt */}
                <polygon points="44,28 50,42 46,42 50,58 40,42 44,42" fill="var(--color-gold)" opacity="0.9"/>
              </svg>
              <div className="text-center px-8">
                <p
                  className="font-bold text-[var(--color-text)]"
                  style={{ fontSize: "var(--text-xl)", fontFamily: "var(--font-urbanist)" }}
                >
                  Snap a bill
                </p>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Take a photo with your camera or choose one from your gallery
                </p>
              </div>
            </div>

            {/* Tips */}
            <div className="flex flex-col gap-2">
              {[
                { icon: "💡", tip: "Lay the bill flat and hold your phone steady" },
                { icon: "🔆", tip: "Good lighting gives better results" },
                { icon: "🖼️", tip: "Fit the whole bill inside the frame" },
              ].map(({ icon, tip }) => (
                <div key={tip} className="flex items-center gap-3 text-sm text-[var(--color-text-muted)]">
                  <span className="text-base w-6 flex-shrink-0 text-center">{icon}</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          /* ── Captured / error state: show preview ── */
          <div
            className="relative w-full rounded-3xl overflow-hidden bg-[var(--color-surface-2)] border border-[var(--color-border)]"
            style={{ aspectRatio: "3/4", maxHeight: "65dvh" }}
          >
            {preview && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={preview}
                alt="Captured bill"
                className="w-full h-full object-contain"
              />
            )}
          </div>
        )}
      </div>

      {/* Hidden camera input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={handleInputChange}
        aria-label="Take a photo"
      />
      {/* Hidden gallery input (no capture attr) */}
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={handleInputChange}
        aria-label="Choose from gallery"
      />

      {/* ── Sticky footer CTAs ── */}
      <div
        className="fixed bottom-0 left-0 right-0 z-40 bg-[var(--color-surface)] border-t border-[var(--color-border)] px-5 pt-4 flex flex-col gap-3"
        style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom, 0px))" }}
      >
        {state === "captured" && !errorMsg ? (
          <>
            <button
              onClick={handleUpload}
              className="w-full h-14 rounded-2xl text-white font-bold text-base flex items-center justify-center gap-2 disabled:opacity-60 transition-opacity"
              style={{ background: "var(--color-aubergine)", fontFamily: "var(--font-urbanist)" }}
            >
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path d="M4 10l4 4 8-8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Use this photo
            </button>
            <button
              onClick={handleRetake}
              className="w-full h-11 text-[var(--color-aubergine)] font-semibold text-sm"
            >
              Retake
            </button>
          </>
        ) : state === "uploading" ? (
          <button
            disabled
            className="w-full h-14 rounded-2xl text-white font-bold text-base flex items-center justify-center gap-2 opacity-70"
            style={{ background: "var(--color-aubergine)" }}
          >
            <span className="animate-spin-slow">⏳</span>
            Uploading…
          </button>
        ) : state === "error" ? (
          <div className="flex gap-3">
            <button
              onClick={handleUpload}
              className="flex-1 h-12 rounded-2xl text-white text-sm font-semibold"
              style={{ background: "var(--color-aubergine)" }}
            >
              Try again
            </button>
            <button
              onClick={handleRetake}
              className="flex-1 h-12 rounded-2xl border border-[var(--color-border)] text-sm font-medium text-[var(--color-text-secondary)]"
            >
              Retake
            </button>
          </div>
        ) : (
          /* idle */
          <>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full h-14 rounded-2xl text-white font-bold text-base flex items-center justify-center gap-3 transition-opacity"
              style={{ background: "var(--color-aubergine)", fontFamily: "var(--font-urbanist)" }}
            >
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
                <path d="M1 15.5V17a2 2 0 002 2h16a2 2 0 002-2v-1.5M11 3v12M7 7l4-4 4 4" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="11" cy="12" r="3.5" fill="none" stroke="white" strokeWidth="1.5"/>
                <path d="M3 7h2l1-2h10l1 2h2a1 1 0 011 1v8a1 1 0 01-1 1H3a1 1 0 01-1-1V8a1 1 0 011-1z" fill="white" fillOpacity="0.15" stroke="white" strokeWidth="1.3"/>
              </svg>
              <span>Take Photo</span>
              <span className="text-sm font-normal opacity-75">ഫോട്ടോ എടുക്കൂ</span>
            </button>
            <button
              onClick={() => galleryInputRef.current?.click()}
              className="w-full h-11 text-[var(--color-text-secondary)] font-medium text-sm flex items-center justify-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <rect x="1" y="1" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M1 10l4-4 3 3 2-2 5 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                <circle cx="11.5" cy="4.5" r="1.5" fill="currentColor"/>
              </svg>
              Choose from gallery
            </button>
          </>
        )}
      </div>
    </main>
  );
}
