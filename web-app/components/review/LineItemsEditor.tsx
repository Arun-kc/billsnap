"use client";

import { useState, useEffect } from "react";
import BottomSheet from "@/components/ui/BottomSheet";
import { parseAmount } from "@/lib/currency";
import { labels } from "@/lib/i18n/labels";

export interface DraftLineItem {
  item_name?: string;
  quantity?: number;
  unit_price?: number;
  total_price?: number;
}

interface LineItemsEditorProps {
  open: boolean;
  onClose: () => void;
  initialItems: DraftLineItem[];
  onSave: (items: DraftLineItem[]) => void;
}

const EMPTY: DraftLineItem = {};

export default function LineItemsEditor({
  open,
  onClose,
  initialItems,
  onSave,
}: LineItemsEditorProps) {
  const [items, setItems] = useState<DraftLineItem[]>(initialItems);

  useEffect(() => {
    if (open) setItems(initialItems.length ? initialItems : [{ ...EMPTY }]);
  }, [open, initialItems]);

  const update = (idx: number, patch: Partial<DraftLineItem>) => {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  };

  const remove = (idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const add = () => {
    setItems((prev) => [...prev, { ...EMPTY }]);
  };

  const handleSave = () => {
    const cleaned = items.filter(
      (it) =>
        it.item_name?.trim() ||
        it.quantity !== undefined ||
        it.unit_price !== undefined ||
        it.total_price !== undefined
    );
    onSave(cleaned);
    onClose();
  };

  const inputBase =
    "w-full h-11 rounded-xl border border-[var(--color-border)] px-3 bg-white text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-aubergine)] focus:ring-opacity-30 focus:border-[var(--color-aubergine)] transition-all text-sm";

  return (
    <BottomSheet open={open} onClose={onClose} title="Edit items · വസ്തുക്കൾ തിരുത്തുക">
      <div className="flex flex-col gap-3 px-5 pt-3 pb-4">
        {items.map((item, idx) => (
          <div
            key={idx}
            className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 flex flex-col gap-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium text-[var(--color-text-muted)]">
                Item {idx + 1}
              </span>
              <button
                type="button"
                onClick={() => remove(idx)}
                aria-label={`Remove item ${idx + 1}`}
                className="text-xs font-medium text-[var(--color-warning)] min-w-[44px] min-h-[32px]"
              >
                Remove
              </button>
            </div>

            <input
              type="text"
              className={inputBase}
              placeholder="Item name"
              value={item.item_name ?? ""}
              onChange={(e) => update(idx, { item_name: e.target.value })}
            />

            <div className="grid grid-cols-3 gap-2">
              <input
                type="text"
                inputMode="decimal"
                className={inputBase}
                placeholder="Qty"
                value={item.quantity ?? ""}
                onChange={(e) => update(idx, { quantity: parseAmount(e.target.value) })}
              />
              <input
                type="text"
                inputMode="decimal"
                className={inputBase}
                placeholder="Price"
                value={item.unit_price ?? ""}
                onChange={(e) => update(idx, { unit_price: parseAmount(e.target.value) })}
              />
              <input
                type="text"
                inputMode="decimal"
                className={inputBase}
                placeholder="Total"
                value={item.total_price ?? ""}
                onChange={(e) => update(idx, { total_price: parseAmount(e.target.value) })}
              />
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={add}
          className="w-full h-12 rounded-2xl border-2 border-dashed border-[var(--color-border)] text-sm font-medium text-[var(--color-aubergine)] hover:bg-[var(--color-surface-2)] transition-colors"
        >
          + {labels.addItem.en} · {labels.addItem.ml}
        </button>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 h-12 rounded-2xl border border-[var(--color-border)] text-sm font-medium text-[var(--color-text)]"
          >
            {labels.cancel.en}
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="flex-1 h-12 rounded-2xl text-white text-sm font-semibold"
            style={{ background: "var(--color-aubergine)" }}
          >
            Done · ശരി
          </button>
        </div>
      </div>
    </BottomSheet>
  );
}
