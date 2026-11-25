# 07: Contract — delete StatusStore, PipelineTracker, ProgressIndicator

**What to build:** The old centralized status system is deleted: `statusStore.ts`, `PipelineTracker.tsx`, and `ProgressIndicator.tsx` are removed, along with any remaining imports, types, and helpers that only they used. Background-task toasts (startup token refresh, eBay sync, image-metadata sync) are rewired to call the direct toast API from ticket 01 instead of the store, with unchanged behavior. After this ticket, no centralized status store or step tracker exists anywhere in the codebase.

**Blocked by:** 02 (Title Search), 03 (Download + Render), 04 (Create Listing), 05 (Upload to eBay), 06 (Research Pipeline)

**Status:** done

- [ ] `statusStore.ts`, `PipelineTracker.tsx`, `ProgressIndicator.tsx` deleted; zero remaining references
- [ ] Background tasks fire their toasts through the direct toast API; behavior unchanged
- [ ] Dead store-only helpers/types cleaned up
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
- [ ] Manual smoke: every workflow still shows per-step status and errors inline
