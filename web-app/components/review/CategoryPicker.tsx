"use client";

import BottomSheet from "@/components/ui/BottomSheet";

const CATEGORIES = [
  "Electrical Supplies",
  "Tools & Equipment",
  "Packaging",
  "Office & Stationery",
  "Transport & Delivery",
  "Groceries",
  "Medical",
  "Services",
  "Utilities",
  "Other",
];

interface CategoryPickerProps {
  value?: string;
  onChange: (category: string) => void;
  open: boolean;
  onClose: () => void;
}

export default function CategoryPicker({
  value,
  onChange,
  open,
  onClose,
}: CategoryPickerProps) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Select Category">
      <ul className="pb-4">
        {CATEGORIES.map((cat) => (
          <li key={cat}>
            <button
              className="w-full text-left px-5 py-4 text-base text-[var(--color-text)] flex items-center justify-between min-h-[52px] hover:bg-[var(--color-surface-2)] transition-colors"
              onClick={() => {
                onChange(cat);
                onClose();
              }}
            >
              {cat}
              {value === cat && (
                <span className="text-[var(--color-aubergine)] text-lg">✓</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </BottomSheet>
  );
}
