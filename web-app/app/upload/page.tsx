"use client";

import { useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { uploadBill } from "@/lib/api";

type UploadState = "idle" | "captured" | "uploading" | "error";

const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>("idle");
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileSelect = useCallback((f: File) => {
    if (!f.type.startsWith("image/")) {
      if (f.type === "application/pdf") {
        setErrorMsg("PDF upload is coming soon! Please use a photo for now.");
      } else {
        setErrorMsg("Only JPEG and PNG photos are supported.");
      }
      return;
    }
    if (f.size > MAX_FILE_BYTES) {
      setErrorMsg(
        "This photo is too large (max 10 MB). Try lowering your camera quality, or crop the image."
      );
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
    // Reset input so same file can be re-selected
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
      setErrorMsg("Couldn't upload the bill. Please check your connection and try again.");
    }
  };

  return (
    <main className="min-h-dvh flex flex-col bg-[var(--color-surface)]">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 pt-safe-top py-4 border-b border-[var(--color-border)]">
        <button
          onClick={() => router.back()}
          className="text-[var(--color-text-secondary)] text-sm font-medium min-w-[44px] min-h-[44px] flex items-center"
        >
          ← Back
        </button>
        <span className="text-sm font-medium text-[var(--color-text-muted)]">
          Step 1 / 3
        </span>
      </header>

      <div className="flex flex-col flex-1 px-5 pt-6 pb-40 gap-5">
        {/* Error banner */}
        {errorMsg && (
          <div className="rounded-xl border border-[var(--color-warning)] bg-[var(--color-warning-bg)] p-4 text-sm text-[var(--color-warning)]">
            ⚠️ {errorMsg}
          </div>
        )}

        {/* Preview / placeholder */}
        <div
          className="relative w-full rounded-2xl overflow-hidden border-2 border-dashed border-[var(--color-border-strong)] bg-[var(--color-surface-2)]"
          style={{ aspectRatio: "9/16", maxHeight: "60dvh" }}
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={preview}
              alt="Captured bill"
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--color-text-muted)]">
              <svg
                width="56"
                height="56"
                viewBox="0 0 56 56"
                fill="none"
                aria-hidden="true"
              >
                <rect
                  x="10"
                  y="6"
                  width="36"
                  height="44"
                  rx="3"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <line x1="18" y1="16" x2="38" y2="16" stroke="currentColor" strokeWidth="2" />
                <line x1="18" y1="22" x2="38" y2="22" stroke="currentColor" strokeWidth="2" />
                <line x1="18" y1="28" x2="30" y2="28" stroke="currentColor" strokeWidth="2" />
              </svg>
              <p className="text-sm text-center px-6">
                Hold the bill flat and fit it inside the frame
              </p>
            </div>
          )}
        </div>

        {!preview && (
          <p className="text-sm text-[var(--color-text-muted)] text-center -mt-2">
            Hold the bill flat and fit it inside the box
          </p>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={handleInputChange}
        aria-label="Take or choose a photo"
      />

      {/* Sticky footer CTAs */}
      <div
        className="fixed bottom-0 left-0 right-0 z-40 bg-[var(--color-surface)] border-t border-[var(--color-border)] px-5 pt-4 flex flex-col gap-3"
        style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom, 0px))" }}
      >
        {state === "captured" ? (
          <>
            <button
              onClick={handleUpload}
              className="w-full h-14 rounded-2xl text-white font-semibold text-base flex flex-col items-center justify-center gap-0.5 disabled:opacity-60 transition-opacity"
              style={{ background: "var(--color-aubergine)" }}
            >
              <span>✓ Use this photo</span>
            </button>
            <button
              onClick={handleRetake}
              className="w-full h-11 text-[var(--color-aubergine)] font-medium text-sm"
            >
              Retake
            </button>
          </>
        ) : (
          <>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full h-14 rounded-2xl text-white font-semibold text-base flex flex-col items-center justify-center gap-0.5 transition-opacity"
              style={{ background: "var(--color-aubergine)" }}
            >
              <span>📷 Take Photo</span>
              <span className="text-xs font-normal opacity-80">ഫോട്ടോ എടുക്കൂ</span>
            </button>
            <button
              onClick={() => {
                // Gallery pick — remove capture attribute
                if (fileInputRef.current) {
                  fileInputRef.current.removeAttribute("capture");
                  fileInputRef.current.click();
                  // Restore after tick
                  setTimeout(() => {
                    fileInputRef.current?.setAttribute("capture", "environment");
                  }, 500);
                }
              }}
              className="w-full h-11 text-[var(--color-text-secondary)] font-medium text-sm"
            >
              Choose from gallery
            </button>
          </>
        )}

        {state === "error" && (
          <div className="flex gap-3">
            <button
              onClick={handleUpload}
              className="flex-1 h-11 rounded-xl text-white text-sm font-medium"
              style={{ background: "var(--color-aubergine)" }}
            >
              Try again
            </button>
            <button
              onClick={handleRetake}
              className="flex-1 h-11 rounded-xl border border-[var(--color-border)] text-sm font-medium text-[var(--color-text-secondary)]"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
