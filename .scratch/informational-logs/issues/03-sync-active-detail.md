# 03: sync_active — SKU lists

**What to build:** An active-sync log row shows "N active · M newly inactive · K updated" and expands to two sections: "Newly inactive" (listings that had an eBay ID but no longer match an active eBay listing) and "Updated" (listings whose local data changed during the sync). Today only bare counts are logged, so there is no way to tell which listings changed. The row also gets a proper label ("Sync (Active)") and a filter chip.

**Blocked by:** 01 (Restock — expandable failure detail) — reuses the generalized multi-section expand panel.

**Status:** resolved

- [ ] Backend sync_active log entry includes `newly_inactive_skus` (the existing not-found list) and `updated_skus` alongside the counts.
- [ ] Frontend label + filter chip exist for `sync_active`; detail line reads "N active · M newly inactive · K updated".
- [ ] Expanded panel shows Newly inactive and Updated sections with lazy-resolved titles.
- [ ] Old sync_active entries (counts only) still render as a one-liner.
- [ ] `cd frontend && npm run build` (or `tsc`) passes.
