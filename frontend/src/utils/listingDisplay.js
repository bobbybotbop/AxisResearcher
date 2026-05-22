export function formatPrice(value, currency = "USD") {
  if (value === undefined || value === null || value === "N/A") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return `$${value}`;
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `$${value}`;
  }
}

/** e.g. 3/7/2026, 10:08 PM — no leading zeros on month/day; local time. */
export function formatListingDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const y = d.getFullYear();
    const time = d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return `${m}/${day}/${y}, ${time}`;
  } catch {
    return "—";
  }
}

export function formatCategoryShort(categoryId) {
  const id = String(categoryId ?? "—");
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}
