# 05: Lazy title resolution + unique row keys

**What to build:** Two cross-cutting fixes to the Activity Log. (a) Expanded SKU rows show each listing's title next to its SKU: the Logs tab fetches the listings index once and builds a sku→title map, so any expanded section can display titles without a per-SKU fetch; SKUs not in the map (deleted/hidden/manual) fall back to a snapshotted title when the log entry carries one, else just the SKU. (b) Row keys and expand-state keys switch from the raw timestamp to a collision-proof composite (timestamp + event + index), so two log entries written within the same timer tick no longer share a React key or toggle each other's expansion.

**Blocked by:** None (can start immediately, in parallel with 01)

**Status:** resolved

- [ ] Logs tab fetches the listings index once on mount and builds a sku→title map.
- [ ] Expanded SKU rows render the resolved title next to the SKU, with graceful fallback (snapshot title, else SKU only) when the SKU is not in the map.
- [ ] Row key / expand-state key is a composite of timestamp, event, and index; rapid successive events expand independently.
- [ ] `cd frontend && npm run build` (or `tsc`) passes.
