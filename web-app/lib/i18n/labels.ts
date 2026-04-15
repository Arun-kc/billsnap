// TODO(i18n): Malayalam strings below are machine-suggested placeholders.
// Must be reviewed with a native Malayalam speaker (Arun's father) before
// V1 external release. Do not translate automatically in CI.

export interface BilingualLabel {
  en: string;
  ml: string;
}

export const labels = {
  vendor: { en: "Vendor / Shop name", ml: "കട / വ്യാപാരി" },
  billNumber: { en: "Bill / Invoice number", ml: "ബിൽ നമ്പർ" },
  date: { en: "Date", ml: "തീയതി" },
  docType: { en: "Document type", ml: "രേഖയുടെ തരം" },
  category: { en: "Category", ml: "വിഭാഗം" },
  total: { en: "Total amount (₹)", ml: "മൊത്തം തുക" },
  taxable: { en: "Taxable amount", ml: "നികുതി വിധേയമായ തുക" },
  cgst: { en: "CGST", ml: "സി‑ജി‑എസ്‑ടി" },
  sgst: { en: "SGST", ml: "എസ്‑ജി‑എസ്‑ടി" },
  igst: { en: "IGST", ml: "ഐ‑ജി‑എസ്‑ടി" },
  gstin: { en: "Vendor GSTIN", ml: "ജി‑എസ്‑ടി‑ഐ‑എൻ" },
  notes: { en: "Notes (optional)", ml: "കുറിപ്പുകൾ" },
  save: { en: "Confirm & Save", ml: "ശരി" },
  edit: { en: "Edit", ml: "തിരുത്തുക" },
  addItem: { en: "Add item", ml: "വസ്തു ചേർക്കുക" },
  cancel: { en: "Cancel", ml: "റദ്ദാക്കുക" },
  items: { en: "Items", ml: "വസ്തുക്കൾ" },
  editItems: { en: "Edit items", ml: "വസ്തുക്കൾ തിരുത്തുക" },
} as const satisfies Record<string, BilingualLabel>;

export type LabelKey = keyof typeof labels;
