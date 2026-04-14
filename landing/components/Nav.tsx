export default function Nav() {
  return (
    <header className="sticky top-0 z-50 bg-surface/95 backdrop-blur-sm shadow-nav">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4"
      >
        <a
          href="/"
          aria-label="BillSnap home"
          className="font-display text-xl font-bold text-primary tracking-tight"
        >
          BillSnap
        </a>

        <a
          href="#waitlist"
          className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-brand-orange-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 min-h-[44px] inline-flex items-center"
        >
          Join waitlist
        </a>
      </nav>
    </header>
  );
}
