# Distributed step status: per-step StepCard + local state, no Status Store

ADR 0002 centralized all waiting-state UI in a single Status Store rendering one PipelineTracker at the top of each workflow. In practice the workflows are tall: when a user is scrolled down working in a later step, a failure — and its Retry button — rendered above their viewport, with only a bottom-right toast as mitigation. This ADR records the reversal: status and errors live where the user is working, distributed across per-step cards, with each workflow owning its steps' state locally.

**Supersedes ADR 0002 Decisions 1–3 and 6** (Task/Pipeline model, single Status Store, PipelineTracker as the status renderer, inline-error-plus-toast via the store). ADR 0002 Decision 5 (always determinate progress when the count is known) survives unchanged. Decision 4 is amended in part: the toast module is decoupled from the (now deleted) store and called directly. Decisions 7 (skeletons) and 8 are unaffected, though Decision 8's revisit trigger has now fired — see Decision 4 below.

## Decisions

1. **`StepCard` is the unit of step status.** One reusable, fully controlled component per step. Its header shows the step title (which carries the sequence — "Step 1 — Fetch eBay Photos"), a state icon for all four explicit states (dimmed pending / spinner running / persistent subtle success check / red error), and optional determinate progress text ("3 of 8"). The body shows a single-line status text with the current activity message, replaced as it updates — not a scrolling log. On error, the message and a Retry button render inline at the card. There is no PipelineTracker, no ProgressIndicator, and no overall progress indicator anywhere.

2. **Parents orchestrate; steps are dumb.** Each workflow component owns its steps' status, progress, and error in local state and passes them down as props; step content reports up via callbacks. There is no shared status store: Task and Pipeline as status-system concepts, the Status Store, and PipelineTracker are all deleted.

3. **Toasts: errors only from step flows.** `StartupToasts` survives as a standalone, direct-call toast module (`toast.error(msg)`), decoupled from any store. A step failure fires a persist-until-dismissed error toast as a scroll-away safety net; success is shown inline only — no success toasts from step flows.

4. **Background tasks go quiet on success.** ADR 0002 Decision 8 accepted full toasts for background tasks (startup token refresh, eBay sync, image-metadata sync) as temporary noise, with a revisit trigger once the store stabilized. That trigger has fired: the success toast on tab switch is dropped — background success is silent, failures still toast. (The full header-status-indicator replacement envisioned there is not built; silent success plus error toasts is the accepted end state.)

5. **Determinate progress stays where counts are known** (carried over from ADR 0002 Decision 5): header "N of M" text when the total is known, a spinner only for single request/response steps. Long-detail progress (e.g. Blender render ETA) stays in the card body where it already lives.

## Trade-off rationale

ADR 0002's centralization bought consistency — one model, one renderer, one store — but it forced *all* status UI to the top of tall workflows, exactly where the user isn't looking once they're working mid-flow. The distribution in this ADR trades that single point of consistency for status that lives where the user is working: the error and its Retry are at the failed step, not scrolled out of view. Consistency is preserved differently, by making `StepCard` the one controlled component every workflow uses, rather than by centralizing the state.

## Consequences

- All six workflows (Create Listing, Upload to eBay, Image Search, Title Search, Download + Render, Research Pipeline) migrate in one pass; no flag, no parallel systems at the end.
- Existing per-step status streams (NDJSON friendly messages) feed the StepCard status line unchanged — no new backend work.
- Toasts never throw: a broken toast must never break the app.
