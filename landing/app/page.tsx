import Nav from "@/components/Nav";
import WaitlistForm from "@/components/WaitlistForm";

/* ── Inline SVG icons ───────────────────────────────────────── */
function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 flex-shrink-0 text-accent"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 flex-shrink-0 text-rose-400"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

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
    icon: "📋",
    label: "Reads GST, handwritten & printed bills",
  },
  {
    icon: "📱",
    label: "Works on any Android phone",
  },
  {
    icon: "🔒",
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
                    className="rounded-full border border-brand-orange/30 bg-brand-orange-light px-4 py-1.5 text-sm font-medium text-brand-orange-dark"
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
            <div className="rounded-2xl bg-[#FFFBF7] border border-orange-100 px-8 py-10 sm:px-12 sm:py-14">
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

            <div className="mt-10 overflow-hidden rounded-2xl border border-gray-100 shadow-card">
              {/* Column headers */}
              <div className="grid grid-cols-2">
                <div className="bg-rose-50 px-6 py-4 text-center">
                  <span className="font-display text-sm font-bold uppercase tracking-wider text-rose-500">
                    Before BillSnap
                  </span>
                </div>
                <div className="bg-green-50 px-6 py-4 text-center">
                  <span className="font-display text-sm font-bold uppercase tracking-wider text-green-600">
                    After BillSnap
                  </span>
                </div>
              </div>

              {/* Rows */}
              {comparison.map((row, i) => (
                <div
                  key={i}
                  className={`grid grid-cols-2 divide-x divide-gray-100 ${
                    i < comparison.length - 1 ? "border-b border-gray-100" : ""
                  }`}
                >
                  <div className="flex items-start gap-3 bg-rose-50/40 px-6 py-5">
                    <CrossIcon />
                    <p className="text-sm leading-relaxed text-rose-700">
                      {row.before}
                    </p>
                  </div>
                  <div className="flex items-start gap-3 bg-green-50/40 px-6 py-5">
                    <CheckIcon />
                    <p className="text-sm leading-relaxed text-green-700">
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
              {trustSignals.map((signal) => (
                <li
                  key={signal.label}
                  className="flex items-start gap-4 rounded-2xl border border-orange-100 bg-white px-6 py-6 shadow-card"
                >
                  <span
                    className="text-3xl leading-none"
                    role="img"
                    aria-hidden="true"
                  >
                    {signal.icon}
                  </span>
                  <p className="font-medium leading-snug text-brand-text">
                    {signal.label}
                  </p>
                </li>
              ))}
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

      {/* Section 7 — Footer */}
      <footer className="bg-white px-5 py-8 text-center">
        <p className="text-sm text-brand-muted">
          &copy; 2026 BillSnap. Made with ❤️ in Kerala.
        </p>
      </footer>
    </>
  );
}
