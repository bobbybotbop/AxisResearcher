# 05: Testing pipelines report to store + render waiting state via PipelineTracker

**What to build:** Title Search, Image Search, Copy Seller, and Download+Render emit Tasks/Pipelines to the Status Store and render their waiting state via `<PipelineTracker>` (per-step status + active step's determinate progress). Inputs and outputs stay completely the same: whitelisted results, candidate lists, intermediate debug values, and bespoke detail UIs are untouched — only the waiting-state rendering changes.

**Blocked by:** 03 (PipelineTracker component + Create workflow migration)

**Status:** done

- [ ] All four Testing pipelines emit Tasks/Pipelines to the store
- [ ] Each renders waiting state via `<PipelineTracker>`
- [ ] Inputs/outputs (whitelisted results, candidate lists, debug values) are unchanged
- [ ] Bespoke detail UIs still render below the PipelineTracker
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
