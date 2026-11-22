# 04: import — split imported vs updated

**What to build:** An import log row shows "N imported · M updated" instead of a single conflated count, and expands to two sections: "Imported" (new listings brought in from eBay) and "Updated" (listings that already existed locally and were refreshed). Today the log records a single `count` = imported + updated and an `imported_skus` list that is never displayed.

**Blocked by:** 01 (Restock — expandable failure detail) — reuses the generalized multi-section expand panel.

**Status:** resolved

- [ ] Backend import log entry records `imported_count`, `updated_count`, `imported_skus`, and a new `updated_skus` list (replacing the single conflated `count`).
- [ ] Frontend detail line reads "N imported · M updated", falling back to the old `count` field for old entries.
- [ ] Expanded panel shows Imported and Updated sections with lazy-resolved titles.
- [ ] `cd frontend && npm run build` (or `tsc`) passes.
