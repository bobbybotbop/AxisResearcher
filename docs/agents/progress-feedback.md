# Progress feedback standard

Reviewer-enforced standard, applied at review time — not a linter. The streaming-versus-polling choice is a judgement call, so a human (or reviewer agent) makes it, with this doc as the bar.

## The rule

Any operation with more than ~2 seconds of user wait must stream live progress. A silent spinner past ~2s is a review finding.

**Default: NDJSON streaming.** Backend yields `progress_event(step, status)` lines, terminates with exactly one `result_event(data)` or `error_event(msg)`, and returns them via `streaming_response(generator)` (`app.py` ~lines 204-225). Frontend consumes with `fetchWithProgress(url, options, onProgress)` (`frontend/src/utils/fetchWithProgress.ts`). Examples: `/api/create-listing`, `/api/upload-listing`, `/api/generate-text`.

**Exception: task-id polling.** Allowed only when the job has no meaningful intermediate progress — the work is atomic, so there is nothing truthful to report between "started" and "done". Example: image generation (`image_generation_tasks` + `/api/generate-images-status/<task_id>` in `app.py`), where each image is atomic and a per-image progress bar would be fabricated.

## The judgement call

Ask: *can the backend name a real step it is currently on?*

- Multi-step work (fetch → process → save → upload), per-item loops, or token streams — **stream**. Each step/item is a `progress_event`.
- One indivisible call to an external service with no partial state — **poll** a task id, and show an honest indeterminate indicator.
- Under ~2s — neither; a plain request/response is fine.

When in doubt, stream. "We don't know how long it will take" is not a reason to poll — report the current step, not a fake percentage.
