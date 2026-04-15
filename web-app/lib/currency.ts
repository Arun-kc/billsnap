const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatCurrency(amount?: number | null): string {
  if (amount == null) return "—";
  return INR.format(amount);
}

export function formatAmount(amount?: number | null): string {
  if (amount == null) return "";
  return amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function parseAmount(value: string): number | undefined {
  const cleaned = value.replace(/,/g, "").trim();
  const n = parseFloat(cleaned);
  return isNaN(n) ? undefined : n;
}
