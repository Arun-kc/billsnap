import { Check, X, FileText, Smartphone, Shield } from "lucide-react";
import Nav from "@/components/Nav";
import WaitlistForm from "@/components/WaitlistForm";

/* ── Steps data ─────────────────────────────────────────────── */
const steps = [
  {
    number: "01",
    name: "Snap",
    description:
      "Take a photo of any bill with your phone, just like WhatsApp.",
  },
  {
    number: "02",
    name: "Check",
    description:
      "BillSnap reads the bill for you. You just confirm the details look right.",
  },
  {
    number: "03",
    name: "Share",
    description:
      "Download a clean Excel file ready to send to your accountant — in minutes.",
  },
];

/* ── Comparison rows ────────────────────────────────────────── */
const comparison = [
  {
    before: "4–6 hours entering bills every quarter",
    after: "10 minutes to export everything",
  },
  {
    before: "Wait for family to help with Excel",
    after: "Do it yourself from your phone",
  },
  {
    before: "Worry about missing a bill",
    after: "Every bill in one place, always",
  },
];

/* ── Trust signals ──────────────────────────────────────────── */
const trustSignals = [
  {
    icon: FileText,
    label: "Reads GST, handwritten & printed bills",
  },
  {
    icon: Smartphone,
    label: "Works on any Android phone",
  },
  {
    icon: Shield,
    label: "Your bills stay private",
  },
];

/* ── Page ───────────────────────────────────────────────────── */
export default function Home() {
  return (
    <>
      <Nav />

      <main>
        {/* Section 1 — Hero */}
        <section
          aria-labelledby="hero-heading"
          className="bg-surface px-5 py-16 sm:py-24"
        >
          <div className="mx-auto max-w-2xl text-center">
            <h1
              id="hero-heading"
              className="font-display text-4xl font-bold leading-tight text-brand-text sm:text-5xl lg:text-6xl"
            >
              Stop typing bills.{" "}
              <span className="text-primary">Just snap and done.</span>
            </h1>

            <p className="mt-6 text-lg leading-relaxed text-brand-muted sm:text-xl">
              BillSnap reads your shop bills for you and sends a clean report
              straight to your accountant — no typing, no Excel, no stress at
              the end of the quarter.
            </p>

            {/* Trust badges */}
            <div
              className="mt-8 flex flex-wrap justify-center gap-3"
              aria-label="Key features"
            >
              {["🇮🇳 Made in India", "₹0 to try", "Works on WhatsApp"].map(
                (badge) => (
                  <span
                    key={badge}
                    className="rounded-full border border-brand-purple/20 bg-brand-purple-light px-4 py-1.5 text-sm font-medium text-brand-purple"
                  >
                    {badge}
                  </span>
                )
              )}
            </div>

            {/* Waitlist form */}
            <div className="mt-8">
              <WaitlistForm />
            </div>

            <p className="mt-4 text-sm text-brand-muted">
              We are personally onboarding the first 20 shop owners.
            </p>
          </div>
        </section>

        {/* Section 2 — Problem */}
        <section
          aria-labelledby="problem-heading"
          className="bg-white px-5 py-16 sm:py-20"
        >
          <div className="mx-auto max-w-2xl">
            <div className="rounded-2xl bg-surface border border-brand-border px-8 py-10 sm:px-12 sm:py-14">
              <h2
                id="problem-heading"
                className="font-display text-2xl font-bold text-brand-text sm:text-3xl"
              >
                Sound familiar?
              </h2>
              <p className="mt-5 text-lg leading-relaxed text-brand-muted">
                Every few months, you sit down with a pile of bills and spend
                hours entering everything into Excel — or worse, you wait for
                someone else to do it. By the time your accountant gets the
                numbers, half the quarter is already over. There has to be a
                better way. Now there is.
              </p>
            </div>
          </div>
        </section>

        {/* Section 3 — How it works */}
        <section
          aria-labelledby="how-heading"
          className="bg-surface px-5 py-16 sm:py-20"
        >
          <div className="mx-auto max-w-4xl">
            <h2
              id="how-heading"
              className="font-display text-center text-2xl font-bold text-brand-text sm:text-3xl"
            >
              How it works
            </h2>

            <ol className="mt-12 grid gap-8 sm:grid-cols-3" role="list">
              {steps.map((step) => (
                <li key={step.number} className="flex flex-col">
                  <span
                    className="font-display text-5xl font-bold text-primary leading-none"
                    aria-hidden="true"
                  >
                    {step.number}
                  </span>
                  <h3 className="mt-4 font-display text-xl font-bold text-brand-text">
                    {step.name}
                  </h3>
                  <p className="mt-2 text-brand-muted leading-relaxed">
                    {step.description}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Section 4 — Before/After */}
        <section
          aria-labelledby="comparison-heading"
          className="bg-white px-5 py-16 sm:py-20"
        >
          <div className="mx-auto max-w-3xl">
            <h2
              id="comparison-heading"
              className="font-display text-center text-2xl font-bold text-brand-text sm:text-3xl"
            >
              See the difference
            </h2>

            <div className="mt-10 overflow-hidden rounded-2xl border border-brand-border shadow-card">
              {/* Column headers */}
              <div className="grid grid-cols-2">
                <div className="bg-[#F9F0FD] px-6 py-4 text-center">
                  <span className="font-display text-sm font-bold uppercase tracking-wider text-brand-purple">
                    Before BillSnap
                  </span>
                </div>
                <div className="bg-[#E6F4EE] px-6 py-4 text-center">
                  <span className="font-display text-sm font-bold uppercase tracking-wider text-[#1A8C5B]">
                    After BillSnap
                  </span>
                </div>
              </div>

              {/* Rows */}
              {comparison.map((row, i) => (
                <div
                  key={i}
                  className={`grid grid-cols-2 divide-x divide-brand-border ${
                    i < comparison.length - 1 ? "border-b border-brand-border" : ""
                  }`}
                >
                  <div className="flex items-start gap-3 bg-[#F9F0FD]/40 px-6 py-5">
                    <X
                      className="h-5 w-5 flex-shrink-0 text-brand-purple/60 mt-0.5"
                      aria-hidden="true"
                    />
                    <p className="text-sm leading-relaxed text-brand-text/70">
                      {row.before}
                    </p>
                  </div>
                  <div className="flex items-start gap-3 bg-[#E6F4EE]/40 px-6 py-5">
                    <Check
                      className="h-5 w-5 flex-shrink-0 text-[#1A8C5B] mt-0.5"
                      aria-hidden="true"
                    />
                    <p className="text-sm leading-relaxed text-brand-text/80">
                      {row.after}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 5 — Trust block */}
        <section
          aria-labelledby="trust-heading"
          className="bg-surface px-5 py-16 sm:py-20"
        >
          <div className="mx-auto max-w-4xl">
            <div className="text-center">
              <h2
                id="trust-heading"
                className="font-display text-2xl font-bold text-brand-text sm:text-3xl"
              >
                Built for shop owners like you
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-brand-muted">
                BillSnap is built in Kerala, for shop owners like you. We know
                what Indian bills look like — GST invoices, handwritten chits,
                printed receipts. No monthly fee during early access. If it does
                not save you time, you do not pay a thing.
              </p>
            </div>

            <ul
              className="mt-10 grid gap-5 sm:grid-cols-3"
              role="list"
              aria-label="Key benefits"
            >
              {trustSignals.map((signal) => {
                const Icon = signal.icon;
                return (
                  <li
                    key={signal.label}
                    className="flex items-start gap-4 rounded-2xl border border-brand-border bg-white px-6 py-6 shadow-card"
                  >
                    <Icon
                      className="h-6 w-6 flex-shrink-0 text-accent mt-0.5"
                      aria-hidden="true"
                    />
                    <p className="font-medium leading-snug text-brand-text">
                      {signal.label}
                    </p>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        {/* Section 6 — Bottom CTA */}
        <section
          id="waitlist"
          aria-labelledby="cta-heading"
          className="bg-primary px-5 py-16 sm:py-24"
        >
          <div className="mx-auto max-w-xl text-center">
            <h2
              id="cta-heading"
              className="font-display text-3xl font-bold text-white sm:text-4xl"
            >
              Be the first to try it — free.
            </h2>
            <p className="mt-5 text-lg leading-relaxed text-white/80">
              We are letting a small group of shop owners try BillSnap first.
              Enter your number or email and we will reach out personally when
              it is ready.
            </p>

            <div className="mt-8">
              <WaitlistForm buttonText="Save my spot" darkMode />
            </div>

            <p className="mt-4 text-sm text-white/70">
              We are personally onboarding the first 20 shop owners. After that,
              there is a waitlist.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white px-5 py-8 text-center">
        <p className="text-sm text-brand-muted">
          &copy; 2026 BillSnap. Made with care in Kerala.
        </p>
      </footer>
    </>
  );
}
