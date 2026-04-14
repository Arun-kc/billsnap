"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

type FormState = "idle" | "loading" | "success" | "error";

interface WaitlistFormProps {
  buttonText?: string;
  darkMode?: boolean;
}

export default function WaitlistForm({
  buttonText = "Tell me when it's ready",
  darkMode = false,
}: WaitlistFormProps) {
  const [contact, setContact] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const trimmed = contact.trim();
    const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const phoneRe = /^(\+91|0)?[6-9]\d{9}$/;
    if (!emailRe.test(trimmed) && !phoneRe.test(trimmed.replace(/\s/g, ""))) {
      setErrorMessage("Please enter a valid email or 10-digit WhatsApp number.");
      setState("error");
      return;
    }

    setState("loading");
    setErrorMessage("");

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contact: contact.trim() }),
      });

      if (response.ok) {
        setState("success");
        setContact("");
      } else {
        const data = (await response.json()) as { error?: string };
        setErrorMessage(data.error ?? "Something went wrong. Please try again.");
        setState("error");
      }
    } catch {
      setErrorMessage("Could not connect. Please try again.");
      setState("error");
    }
  }

  if (state === "success") {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`rounded-2xl px-6 py-5 text-center ${
          darkMode
            ? "bg-white/20 text-white"
            : "bg-[var(--color-success-light)] text-[var(--color-success)]"
        }`}
      >
        <p className="text-lg font-semibold">
          You&apos;re on the list!
        </p>
        <p className="mt-1 text-sm opacity-80">
          We&apos;ll be in touch on WhatsApp or email.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Join the BillSnap waitlist"
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <label htmlFor="waitlist-contact" className="sr-only">
          Your email or WhatsApp number
        </label>
        <input
          id="waitlist-contact"
          type="text"
          name="contact"
          value={contact}
          onChange={(e) => {
            setContact(e.target.value);
            if (state === "error") {
              setState("idle");
              setErrorMessage("");
            }
          }}
          placeholder="Your email or WhatsApp number"
          autoComplete="off"
          aria-required="true"
          aria-describedby={state === "error" ? "waitlist-error" : undefined}
          className={`min-h-[48px] flex-1 rounded-xl border px-4 py-3 text-base text-brand-text placeholder:text-brand-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors ${
            darkMode
              ? "bg-white/20 border-white/30 text-white placeholder:text-white/60 focus:ring-white"
              : "bg-white border-brand-border"
          } ${state === "error" ? "border-[var(--color-error)]" : ""}`}
        />
        <button
          type="submit"
          disabled={state === "loading"}
          className={`min-h-[48px] rounded-xl px-6 py-3 text-base font-semibold transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed ${
            darkMode
              ? "bg-white text-primary hover:bg-brand-purple-light focus:ring-white focus:ring-offset-primary"
              : "bg-primary text-white hover:bg-brand-purple-dark focus:ring-primary"
          }`}
          aria-label={state === "loading" ? "Saving your spot..." : buttonText}
        >
          {state === "loading" ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>Saving...</span>
            </span>
          ) : (
            buttonText
          )}
        </button>
      </div>

      {state === "error" && errorMessage && (
        <p
          id="waitlist-error"
          role="alert"
          className={`mt-2 text-sm ${darkMode ? "text-red-200" : "text-[var(--color-error)]"}`}
        >
          {errorMessage}
        </p>
      )}
    </form>
  );
}
