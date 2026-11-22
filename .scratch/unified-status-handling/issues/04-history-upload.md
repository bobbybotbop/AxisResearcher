# 04: History / Upload per-card status badges + skeletons

**What to build:** History listing cards (compact rows + detailed cards) show skeleton placeholders while listings load. Bulk upload to eBay shows a per-card status badge (spinner → check/error) so the user sees which listing failed, plus one summary toast ("8 succeeded, 2 failed") with details on click. Bulk delete is a single task with progress plus a summary toast. Sync and restock report through the store.

**Blocked by:** 01 (Status Store + Task/Pipeline model)

**Status:** done

- [ ] History shows skeleton cards while listings load
- [ ] Bulk upload shows per-card status badge (spinner → check/error) plus one summary toast
- [ ] Bulk delete is a single store task with progress plus summary toast
- [ ] Sync and restock report through the store
- [ ] Upload/sync/restock `is*` booleans are replaced by the store
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
