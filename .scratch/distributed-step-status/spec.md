# Distributed Step Status

## Context

The frontend's waiting-state UI is centralized: a `StatusStore` owns all Task/Pipeline state, and each workflow renders a single `PipelineTracker` at the TOP of its container, above all step cards. When a user is scrolled down working in a later step, a failure (with its Retry button) renders above their viewport — the bottom-right toast is the only mitigation. The user wants status **right where they are**: each step card owns its own status display. This reverses ADR 0002 Decisions 1–3 and 6 (Task/Pipeline model, single Status Store, PipelineTracker).

## Confirmed design decisions (from grilling session — do not relitigate)

1. **No PipelineTracker, no ProgressIndicator, no StatusStore.** All three deleted once migration completes. No centralized step tracker UI anywhere; no overall progress indicator — step titles ("Step 1 — Fetch eBay Photos") carry the sequence.
2. **`StepCard` component** — one reusable, fully controlled component. Header shows: step title, state icon (dimmed pending / spinner running / persistent subtle green check success / red error), optional determinate progress text ("3 of 8"). Body contains a **single-line status text** showing the current activity message ("Fetching photos…" → "Comparing image 2 of 5…"), replaced as it updates — not a scrolling log. On `error`: the error message + Retry button render inline at the card. `disabled` prop greys out steps whose dependencies aren't met.
3. **All four states explicit**: pending, running, success, error. Success check is persistent (it's the only way to see which steps are done when scrolled mid-workflow) but subtle.
4. **Parent orchestrates.** Each workflow component owns its steps' state via `useState`, passes `status` / `progress` / `error` / `onRetry` / `disabled` down, and step content reports up via `onStatusChange`-style callbacks. Steps are dumb and reusable.
5. **Toasts: errors only.** `StartupToasts` survives as a standalone toast module (decoupled from any store), exposed via a small direct-call API (e.g. `toast.error(msg)`). Step failures fire an error toast (persist-until-dismissed) as a scroll-away safety net. Success is inline-only — no success toasts from step flows. Background-task toasts (startup token refresh, eBay sync, image-metadata sync) are unchanged in behavior but must call the toast module directly instead of through the store.
6. **Determinate progress stays where counts are known** (ADR 0002 Decision 5 survives): header progress text "N of M"; long-detail progress (Blender render ETA, shot N of M) stays in the card body where it already lives. Spinner only for single request/response steps.
7. **All workflows migrated in one pass** (no flag, no parallel systems at the end): Create Listing, Upload to eBay, Image Search, Title Search, Download + Render, Research Pipeline.
8. **Docs:** new ADR `0003-distributed-step-status.md` superseding the relevant parts of ADR 0002; glossary entries for Task, Pipeline, Status Store, PipelineTracker updated to match the new model.
9. **Existing status streams are reused.** The 3D-finder NDJSON status stream work (`.scratch/3d-finder-status-stream/spec.md`) already emits friendly per-step messages — the status line consumes those, no new backend work.

## Key codebase facts (from exploration)

- `frontend/src/utils/statusStore.ts` — hand-rolled module store; Tasks have `status: pending|running|success|error`, optional `error`/`detail`. Drives `PipelineTracker` and toasts.
- `frontend/src/components/PipelineTracker.tsx` — tracker with per-step icon, inline error + Retry (`:66-79`). Rendered at the top of every workflow container: `CreateWorkflow.tsx:360` (create) and `:956-958` (upload), `ImageSearchSteps.tsx:174`, `TitleSearchPipeline.tsx:367`, `SharedDownloadRender.tsx:586`, `ResearchPipeline.tsx:407`.
- `frontend/src/components/ProgressIndicator.tsx` — legacy prop-driven duplicate of PipelineTracker, no usages found. Delete.
- `frontend/src/components/StartupToasts.tsx` — bottom-right portal toasts; error toasts red, `role="alert"`, persist until dismissed; success auto-dismiss 5s. Becomes the standalone toast module.
- `SharedDownloadRender.tsx` already has true inline errors (`step3Error` `:649`, `step4Error` `:815`) and a determinate render progress bar (`:767-785`) — fold into StepCard pattern.
- No `ErrorBoundary` anywhere; none is added.
- `utils/createPipeline.ts` defines the Create workflow's 5–7 store-pipeline steps; `App.tsx:2875-2984` defines the 2-step Upload pipeline. Both replaced by local state.
- Streaming machinery already exists: `fetchWithProgress` / `fetchWithTextStream` (NDJSON), per-step friendly messages from the 3D-finder status stream work.
- Workflows are NOT wizards with a shared stepper; each is one component owning stacked step cards. Testing-tab flows (Image Search / Title Search → Download+Render) compose via lifted state in `App.tsx:4485-4529`.

## Verification

- Frontend: `cd frontend && npm run build` (tsc + vite) passes.
- Backend: `python -m pytest tests/` from repo root (repo `.venv`) passes.
- Manual: run each workflow end-to-end; each step shows live status in its own card header/status line; a failure shows the error + Retry at the failed step without scrolling, plus an error toast.
