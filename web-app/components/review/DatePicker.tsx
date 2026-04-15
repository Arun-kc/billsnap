"use client";

import { useState } from "react";
import BottomSheet from "@/components/ui/BottomSheet";

interface DatePickerProps {
  value?: string; // YYYY-MM-DD
  onChange: (date: string) => void;
  open: boolean;
  onClose: () => void;
}

function formatForDisplay(iso?: string): string {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
}

export default function DatePicker({ value, onChange, open, onClose }: DatePickerProps) {
  const [inputVal, setInputVal] = useState(value ?? "");

  const handleConfirm = () => {
    if (inputVal) onChange(inputVal);
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Select Date">
      <div className="px-5 py-6 flex flex-col gap-4">
        <input
          type="date"
          value={inputVal}
          max={new Date().toISOString().split("T")[0]}
          onChange={(e) => setInputVal(e.target.value)}
          className="w-full h-14 rounded-xl border border-[var(--color-border)] px-4 text-base text-[var(--color-text)] bg-white focus:outline-none focus:border-[var(--color-aubergine)]"
          style={{ fontSize: "var(--text-base)" }}
        />
        <button
          onClick={handleConfirm}
          className="w-full h-14 rounded-2xl text-white font-semibold text-base"
          style={{ background: "var(--color-aubergine)" }}
        >
          Confirm
        </button>
      </div>
    </BottomSheet>
  );
}

export { formatForDisplay };
