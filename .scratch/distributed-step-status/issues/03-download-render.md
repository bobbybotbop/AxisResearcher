# 03: Download + Render migration

**What to build:** Download (Step 3) and Studio Render (Step 4) become `StepCard`s driven by local state. The existing inline `step3Error`/`step4Error` displays fold into the StepCard error pattern; the determinate render progress (sample N/M, ETA, shot i of N) stays in the card body, with the header showing "shot i of N" when multi-shot. Download stream messages feed the Step 3 status line. Failures show inline error + Retry plus an error toast. Its PipelineTracker render and StatusStore usage are removed. The composed Testing-tab flow (Image/Title Search → Download+Render via lifted state) keeps working.

**Blocked by:** 01 (Toast module + StepCard component + Image Search migration)

**Status:** done

- [ ] Steps 3 and 4 render as `StepCard`s; old `step3Error`/`step4Error` markup removed in favor of the StepCard error pattern
- [ ] Render progress detail (ETA, shot counts) remains visible in the card body; header shows determinate count when known
- [ ] Download status stream messages appear in the Step 3 status line
- [ ] Failed step shows inline error + Retry plus error toast
- [ ] Cross-component composition via lifted state in the Testing tab still works end-to-end
- [ ] No StatusStore / PipelineTracker usage remains in Download + Render
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
