"use client";

function parseMonth(month: string): Date {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1);
}

function formatMonth(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function displayMonth(month: string): string {
  const d = parseMonth(month);
  return d.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

interface MonthSwitcherProps {
  value: string; // YYYY-MM
  onChange: (month: string) => void;
}

export default function MonthSwitcher({ value, onChange }: MonthSwitcherProps) {
  const thisMonth = formatMonth(new Date());
  const isCurrentMonth = value === thisMonth;

  const prev = () => {
    const d = parseMonth(value);
    d.setMonth(d.getMonth() - 1);
    onChange(formatMonth(d));
  };

  const next = () => {
    if (isCurrentMonth) return;
    const d = parseMonth(value);
    d.setMonth(d.getMonth() + 1);
    onChange(formatMonth(d));
  };

  return (
    <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-[var(--color-border)]">
      <button
        onClick={prev}
        className="min-w-[44px] min-h-[44px] flex items-center justify-center text-[var(--color-aubergine)] text-lg font-bold"
        aria-label="Previous month"
      >
        ‹
      </button>
      <span className="text-base font-semibold text-[var(--color-text)]">
        {displayMonth(value)}
      </span>
      <button
        onClick={next}
        disabled={isCurrentMonth}
        className="min-w-[44px] min-h-[44px] flex items-center justify-center text-[var(--color-aubergine)] text-lg font-bold disabled:opacity-30"
        aria-label="Next month"
      >
        ›
      </button>
    </div>
  );
}
