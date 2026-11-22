# 03: PipelineTracker component + Create workflow migration

**What to build:** A reusable `<PipelineTracker>` component renders any Pipeline as a step tracker: per-step status icon (pending/running/done/error), step name, and the active step's determinate progress as text ("3 of 8"). The entire Create workflow (fetch photos → categorize → bg removal → image generation → text generation → create listing) runs as one Pipeline of Tasks reporting to the Status Store. The photo gallery shows skeleton thumbnails while photos fetch. A failed step turns red inline with the error message and a Retry button, plus a toast. This is the reference implementation for PipelineTracker.

**Blocked by:** 01 (Status Store + Task/Pipeline model)

**Status:** done

- [ ] `<PipelineTracker>` renders any Pipeline with per-step status and active-step determinate progress
- [ ] Create workflow runs as one Pipeline of Tasks through the store
- [ ] Photo gallery shows skeleton thumbnails while photos fetch
- [ ] Every step with a known count shows determinate progress; only single request/response steps show a spinner
- [ ] A failed step shows inline red error + Retry button, plus a toast
- [ ] The four `ProgressState` objects and Create's `is*` booleans are replaced by the store
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
