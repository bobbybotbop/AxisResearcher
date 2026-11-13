# 03: Soft-delete mechanism + migration of existing not_found items

**What to build:** Backend support for soft-deleting a listing: a `hidden: true` flag on the listing JSON; the listings API excludes hidden listings from its response. Includes a one-time migration (run at backend startup, idempotent) applying the agreed rules to existing files: `ebay_status: "not_found"` WITH a non-empty eBay listing ID becomes hidden; `not_found` WITHOUT an eBay listing ID stays visible (it becomes a draft under ticket 01). Manual "Delete Selected" (bulk-delete endpoint) remains a hard file delete, unchanged.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] Listings with `hidden: true` never appear in the listings API response
- [ ] Migration soft-deletes existing not_found-with-ID files exactly once and is safe to re-run
- [ ] not_found-without-ID files remain visible after migration
- [ ] Manual bulk-delete still deletes the file from disk
