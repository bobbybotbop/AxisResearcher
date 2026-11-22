# 01: Restock — expandable failure detail + exact errors

**What to build:** When a restock partially or wholly fails, the Activity Log row expands to show not just the restocked listings but also a "Failed" section (each failed SKU with the exact eBay error string) and a "Not found on eBay" section (SKUs that no longer exist on eBay). Today those failed/not-found SKUs are written to the log but never displayed, so failures are invisible. This ticket also introduces the generalized multi-section expand panel that the sync and import tickets reuse.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] Backend restock log entry includes the per-SKU exact error strings (the `failed_errors` dict already computed in the restock flow) alongside the existing `failed_skus` / `not_found_skus` fields.
- [ ] Expanded restock panel renders three headed sections: Restocked (existing SKU + eBay link + View), Failed (SKU + exact error text, danger styling), Not found on eBay (SKU list).
- [ ] The expand panel is implemented as a reusable multi-section component (heading + SKU rows) rather than restock-specific markup, so later tickets can declare their own sections.
- [ ] Old restock log entries (no `failed_errors`) still render without the Failed section.
- [ ] `cd frontend && npm run build` (or `tsc`) passes.
