# Unified status handling: Task/Pipeline model + single Status Store

The frontend's status handling was fragmented: three overlapping toast mechanisms (`ToastContainer` top-center, `StartupToasts` bottom-right, inline messages), four parallel `ProgressState` objects, and ~30 independent `is*` boolean flags concentrated in `App.tsx`. Each feature wired its own loading, progress, and error UI. This ADR records the decision to replace all of it with one model and one store.

## Decisions

1. **Task/Pipeline domain model.** A **Task** is the atomic unit of async work: id, name, status (`pending`/`running`/`success`/`error`), optional progress (`current`/`total`), optional error. A **Pipeline** is a named, ordered sequence of Tasks with a current index. A Pipeline renders as a step tracker; a standalone Task renders as a progress bar or toast. This replaces the four `ProgressState` objects and the `is*` booleans.

2. **Single Status Store, scoped strictly to waiting-state UI.** One frontend store owns all Task and Pipeline state. Its scope is *only* what the user sees while waiting: spinners, progress bars, skeletons, toasts, step statuses. It never touches feature inputs or outputs (whitelisted results, candidate lists, form values, intermediate debug values) — those stay in the features that own them. This boundary is deliberate: the store is a status renderer, not a state-management replacement.

3. **PipelineTracker is a pure status renderer.** One component renders any Pipeline as a step tracker: per-step status icon, step name, and the active step's determinate progress as text ("3 of 8"). It can display any step's waiting state regardless of whether that step also has a bespoke detail UI below it. Used by the Create workflow and all Testing pipelines.

4. **One toast system, bottom-right.** `StartupToasts` (which already exposes the right handle API: `startTaskToast` → `update`/`succeed`/`fail`) becomes the store's toast module. `ToastContainer` is deleted and its callers migrated. Success toasts auto-dismiss; error toasts persist.

5. **Always determinate when the count is known.** If the backend knows the total (N images, N steps), the UI shows a bar with "3 of 12". A spinner is used only for single request/response calls where no count exists. The NDJSON streaming protocol already carries counts for nearly everything.

6. **Errors are inline at the step plus a toast.** A failed Pipeline step turns red with the error message and a Retry button; a toast also fires so the failure is noticed when scrolled elsewhere. Standalone task errors show inline where the result would appear, plus a toast.

7. **Skeletons for card/row layouts, loading bar for tables.** History, Saved 3D Files, and the Create photo gallery get skeleton placeholders; Data Browser and Logs get a top loading bar.

8. **Full toasts for background tasks — temporary.** Background tasks (startup token refresh, eBay sync, image-metadata sync) currently fire full toasts. This is known noise (3+ toasts on every app open, a toast on every image edit) and is accepted temporarily. **Revisit trigger:** once the unified store is stable, replace background-task toasts with a subtle header status indicator that surfaces only failures.

## Migration order

Settings + Saved 3D Files first (prove the store API on low-stakes ground) → Create workflow (the PipelineTracker reference implementation) → History/Upload (per-card status badges) → Testing pipelines. Each migration is a separate, shippable step.

## Consequences

- `App.tsx` shrinks substantially as `is*` booleans and `ProgressState` objects move into the store.
- The `StartupToasts` handle API generalizes into the store's `startTask`/`startPipeline` API, so the codebase already knows the shape.
- Deleting `ToastContainer` touches ~20 call sites; done as one mechanical migration.
- Testing pipelines keep their bespoke detail UIs (inputs/outputs unchanged) but report status through the store and render waiting state via PipelineTracker.
