# 02: sync_startup — SKU lists + removed-title snapshots

**What to build:** A startup-sync log row shows "N removed · M healed" and expands to two sections: "Removed (ended on eBay)" — listings soft-deleted because they ended outside the app, each showing its title — and "Healed" — listings that came back to life. Because removed listings are hidden at sync time, their titles must be snapshotted into the log entry at deletion time; healed titles resolve lazily. The row also gets a proper label ("Sync (Startup)") and a filter chip instead of rendering raw "sync_startup" with an empty detail line.

**Blocked by:** 01 (Restock — expandable failure detail) — reuses the generalized multi-section expand panel.

**Status:** resolved

- [ ] Backend sync_startup log entry includes `removed_skus`, `healed_skus`, and `removed_titles` (a sku→title map snapshotted before soft-deletion, read from the listing's product title).
- [ ] Frontend label + filter chip exist for `sync_startup`; detail line reads "N removed · M healed".
- [ ] Expanded panel shows Removed (titles from the snapshotted map) and Healed (lazy-resolved titles) sections.
- [ ] Old sync_startup entries (counts only) still render as a one-liner.
- [ ] `cd frontend && npm run build` (or `tsc`) passes.
