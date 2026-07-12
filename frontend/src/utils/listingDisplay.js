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

/** e.g. "07/11/2026, 14:43" — MM/DD/YYYY, local time 24 h. */
export function formatListingDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const yr = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${mo}/${day}/${yr}, ${hh}:${mm}`;
  } catch {
    return "—";
  }
}

export function formatCategoryShort(categoryId) {
  const id = String(categoryId ?? "—");
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}
