export default function Nav() {
  return (
    <header className="sticky top-0 z-50 bg-surface/95 backdrop-blur-sm shadow-nav">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4"
      >
        {/* Logo lockup */}
        <a
          href="/"
          aria-label="BillSnap home"
          className="flex items-center gap-2.5"
        >
          {/* Snap Bill mark — 32×32 */}
          <svg
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="nav-bill" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#7340BE" />
                <stop offset="100%" stopColor="#2A1450" />
              </linearGradient>
              <linearGradient id="nav-fold" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#E8BF45" />
                <stop offset="100%" stopColor="#A07A1A" />
              </linearGradient>
              <linearGradient id="nav-bolt" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F5DC87" />
                <stop offset="100%" stopColor="#C9A227" />
              </linearGradient>
            </defs>

            {/* Bill (tilted) */}
            <g transform="rotate(-8 16 16)">
              {/* Drop shadow */}
              <path
                d="M7 7 C7 6.1 7.7 5.5 8.5 5.5H19L25 11.5V26 C25 26.9 24.3 27.5 23.5 27.5H8.5 C7.7 27.5 7 26.9 7 26Z"
                fill="#0E0520"
                opacity="0.3"
                transform="translate(1.5 1.5)"
              />
              {/* Bill body */}
              <path
                d="M7 7 C7 6.1 7.7 5.5 8.5 5.5H19L25 11.5V26 C25 26.9 24.3 27.5 23.5 27.5H8.5 C7.7 27.5 7 26.9 7 26Z"
                fill="url(#nav-bill)"
              />
              {/* Folded corner */}
              <path
                d="M19 5.5L25 11.5H20.5 C19.7 11.5 19 10.8 19 10Z"
                fill="url(#nav-fold)"
              />
              {/* Ruled lines */}
              <line
                x1="10" y1="16" x2="21" y2="16"
                stroke="rgba(255,255,255,0.22)"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
              <line
                x1="10" y1="20" x2="19" y2="20"
                stroke="rgba(255,255,255,0.15)"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </g>

            {/* Lightning bolt — top-right, upright */}
            <path
              d="M22,3 L15.5,13.5 L19.5,13.5 L17.5,22 L25.5,11 L21.5,11 Z"
              fill="url(#nav-bolt)"
            />
          </svg>

          {/* Wordmark */}
          <span className="font-display text-xl font-bold tracking-tight">
            <span className="text-brand-text">Bill</span>
            <span className="text-primary">Snap</span>
          </span>
        </a>

        <a
          href="#waitlist"
          className="rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold text-white transition-colors duration-150 hover:bg-brand-purple-dark focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 min-h-[44px] inline-flex items-center"
        >
          Join waitlist
        </a>
      </nav>
    </header>
  );
}
