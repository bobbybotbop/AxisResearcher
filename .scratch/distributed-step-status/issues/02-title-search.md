# 02: Title Search migration

**What to build:** The Title Search pipeline (fetch eBay listing → optimize title & search → confirm match, including the shortened-query retry and image confirmation) renders each step as a `StepCard` with parent-orchestrated sequencing via local state. The existing NDJSON status stream messages feed each step's status line; determinate counts appear in the header where known; opaque external calls (SerpAPI) show phase messages only, no fabricated progress. Failures show inline error + Retry at the failed step plus an error toast. Its PipelineTracker render and StatusStore usage are removed.

**Blocked by:** 01 (Toast module + StepCard component + Image Search migration)

**Status:** done

- [ ] All Title Search steps render as `StepCard`s driven by local state in the workflow component
- [ ] Status lines show the friendly stream messages; phases only for SerpAPI calls, "N of M" only where real counts exist
- [ ] Step dependencies (can't confirm match before search succeeds) enforced via `disabled`
- [ ] Failed step shows inline error + Retry plus error toast; retry re-runs from the failed step
- [ ] No StatusStore / PipelineTracker usage remains in Title Search
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
