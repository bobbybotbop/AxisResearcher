# 06: Shared async toast notification system for startup tasks

**What to build:** A small toast notification system for app-initialization tasks: non-blocking, stacked toasts in a screen corner supporting multiple concurrent async tasks tracked independently. Each task shows progress ("Syncing with eBay…") then result ("eBay sync complete — 2 listings removed from history"). Success toasts auto-dismiss after ~5 seconds; error toasts persist until manually dismissed. Startup tasks (eBay status sync from ticket 05, the existing quantity refresh) fire asynchronously in parallel — not sequentially — and both report through this system. The app is fully usable while they run.

**Blocked by:** 05: Startup eBay status sync with 24h cooldown, soft-deletes externally-ended

**Status:** done

- [ ] Multiple startup tasks can show toasts simultaneously, each with its own progress→result lifecycle
- [ ] Success toasts auto-dismiss (~5s); error toasts persist until dismissed
- [ ] eBay status sync and quantity refresh both report through the toasts and run in parallel
- [ ] UI never blocks on startup tasks
