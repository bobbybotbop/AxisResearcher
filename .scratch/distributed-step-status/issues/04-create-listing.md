# 04: Create Listing migration

**What to build:** The Create workflow (fetch listing from eBay → initial JSON → categorize images → remove backgrounds → generate images → generate text → create listing) renders each step as a `StepCard` driven by local state in the workflow component, replacing the `createPipeline.ts` StatusStore wiring and both `ProgressState` remnants. Determinate counts ("3 of 8" images) show in the header; streamed text generation keeps writing into the inputs as today, with the step status line narrating ("AI is writing…"). Optional steps (categorize, bg removal) appear `disabled`/pending when skipped by settings. The phase-based retry logic (fetch / images / create) survives as parent-owned retry handlers per step. Failures show inline error + Retry at the failed step plus an error toast. The photo-gallery skeleton thumbnails stay as-is.

**Blocked by:** 01 (Toast module + StepCard component + Image Search migration)

**Status:** done

- [ ] Every Create step renders as a `StepCard`; the top-of-container PipelineTracker is removed
- [ ] Determinate progress in headers wherever counts are known; spinner only for single request/response steps
- [ ] Retry from a failed step re-runs the correct phase without restarting completed steps
- [ ] Text generation streaming into inputs is unchanged; step status line narrates progress
- [ ] Skipped optional steps render disabled/pending rather than running
- [ ] Failed step shows inline error + Retry plus error toast
- [ ] `utils/createPipeline.ts` store wiring removed; no StatusStore usage remains in the Create workflow
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
