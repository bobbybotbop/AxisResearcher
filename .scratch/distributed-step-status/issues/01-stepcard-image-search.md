# 01: Toast module + StepCard component + Image Search migration

**What to build:** The tracer bullet. `StartupToasts` gains a small direct-call API (e.g. `toast.error(msg)` / `toast.success(msg)`) usable without the StatusStore. A reusable, fully controlled `StepCard` component renders: a header with step title, state icon (dimmed pending / spinner running / persistent subtle green check success / red error) and optional determinate progress text ("3 of 8"); a single-line status text showing the current activity message, replaced as it updates; and on error the message + Retry button inline at the card. A `disabled` prop greys out steps whose dependencies aren't met. The Image Search workflow (fetch eBay photos → reverse image search) runs entirely on local `useState` in its parent through `StepCard` — no StatusStore, no PipelineTracker. Step failures show inline error + Retry at the failed step AND fire an error toast; success shows inline only, no toast. This is the reference implementation for all other migrations.

**Blocked by:** None (can start immediately)

**Status:** done

- [ ] Direct-call toast API exists and works without the StatusStore; error toasts persist until dismissed
- [ ] `StepCard` renders all four states in the header, single-line status text, optional "N of M" progress, inline error + Retry, and `disabled` state
- [ ] Image Search steps consume the existing NDJSON status stream messages into the status line; determinate counts shown where known
- [ ] Image Search uses no StatusStore and no PipelineTracker; its PipelineTracker render is removed
- [ ] Step failure shows error + Retry at the failed step without scrolling, plus an error toast; success shows no toast
- [ ] Other workflows are untouched and still work through the old store (expand phase — nothing else breaks)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
