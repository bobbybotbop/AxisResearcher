# 06: Research Pipeline migration

**What to build:** The Research Pipeline (checking API budget → collecting seller listings → fetching listing details → computing metrics) renders each step as a `StepCard` driven by local state, replacing its PipelineTracker. The streaming per-listing metrics sub-progress feeds the status line and determinate header counts where known. Failures show inline error + Retry plus an error toast.

**Blocked by:** 01 (Toast module + StepCard component + Image Search migration)

**Status:** done

- [ ] All Research Pipeline steps render as `StepCard`s driven by local state
- [ ] Per-listing metrics progress appears in the status line / header counts where real counts exist
- [ ] Failed step shows inline error + Retry plus error toast
- [ ] No StatusStore / PipelineTracker usage remains in the Research Pipeline
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
