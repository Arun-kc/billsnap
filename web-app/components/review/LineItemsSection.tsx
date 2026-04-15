"use client";

import { useMemo } from "react";
import { formatAmount } from "@/lib/currency";
import { labels } from "@/lib/i18n/labels";
import type { DraftLineItem } from "./LineItemsEditor";

interface LineItemsSectionProps {
  items: DraftLineItem[];
  onEdit: () => void;
}

export default function LineItemsSection({ items, onEdit }: LineItemsSectionProps) {
  const { count, total } = useMemo(() => {
    const c = items.length;
    const t = items.reduce((sum, it) => sum + (it.total_price ?? 0), 0);
    return { count: c, total: t };
  }, [items]);

  return (
    <div className="flex items-center justify-between p-4 rounded-2xl bg-white border border-[var(--color-border)]">
      <div className="flex flex-col gap-0.5">
        <p className="text-xs font-medium text-[var(--color-text-muted)]">
          {labels.items.en}{" "}
          <span lang="ml" style={{ fontFamily: "'Noto Sans Malayalam', sans-serif" }}>
            · {labels.items.ml}
          </span>
        </p>
        <p className="text-sm font-semibold text-[var(--color-text)]">
          {count === 0
            ? "No items yet"
            : `${count} ${count === 1 ? "item" : "items"}${
                total > 0 ? ` · ₹${formatAmount(total)}` : ""
              }`}
        </p>
      </div>
      <button
        type="button"
        onClick={onEdit}
        className="h-10 px-4 rounded-xl text-sm font-semibold text-[var(--color-aubergine)] border border-[var(--color-aubergine)] min-w-[64px]"
      >
        {count === 0 ? labels.addItem.en : labels.edit.en}
      </button>
    </div>
  );
}
