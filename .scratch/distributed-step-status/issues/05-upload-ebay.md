# 05: Upload to eBay migration

**What to build:** The Upload to eBay flow (preparing listing data → uploading to eBay) renders its steps as `StepCard`s driven by local state, replacing the upload PipelineTracker near the upload button. Per-card badge status (`CardUploadBadge`) and the batch summary toast behavior stay as-is; step failures show inline error + Retry plus an error toast.

**Blocked by:** 04 (Create Listing migration) — both touch the CreateWorkflow component; land after it to avoid conflicts

**Status:** done

- [ ] Upload steps render as `StepCard`s; upload PipelineTracker removed
- [ ] Per-card upload badges and batch summary toast unchanged
- [ ] Failed upload step shows inline error + Retry plus error toast
- [ ] No StatusStore usage remains in the Upload flow
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
