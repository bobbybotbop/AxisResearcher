# 07: Stream Blender render progress to Step 4

**What to build:** When the user clicks Render in Step 4, the status area shows a live progress bar driven by Blender's own output instead of sitting silent for ~21 seconds. The `/api/render` endpoint switches from task-id polling to the repo's existing NDJSON streaming machinery (`progress_event`/`result_event`/`error_event` + `streaming_response`, consumed on the frontend by `fetchWithProgress`). The backend launches Blender with `subprocess.Popen` and a stdout line reader (replacing `capture_output`), parses the `Sample N/M` and `Remaining:MM:SS` checkpoints Cycles prints, and emits them as progress events carrying `current`/`total` sample counts and the ETA. Step 4's status area renders a thin progress bar plus a line like "Rendering — sample 34/48, ~8s remaining." The `result` event carries the image URL and filename directly (no more `/api/render-status` polling for this endpoint); failures end the stream with a friendly `error` event and the panel resets so the user can retry.

Known caveat (acceptable, do not over-engineer): with adaptive sampling the checkpoints are coarse — a 512px test printed samples 0, 1, then 48 — so at 1024² the bar may jump rather than glide. Still a large improvement over silence.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] Clicking Render in Step 4 shows a live progress bar and a "sample N/M, ~Xs remaining" line that updates as Blender runs, with no task-id polling
- [ ] `/api/render` streams NDJSON via the shared helpers; Blender is run with `Popen` + a stdout line reader (not `capture_output`); the 90s timeout still kills a hung render and ends the stream with a friendly error
- [ ] The `result` event delivers the image URL + filename; the panel shows the image and download button exactly as before; each existing failure mode (missing Blender, conversion failure, unsupported format, timeout) still ends in a clear panel error
- [ ] The old `/api/render-status` polling path and the now-unused `render_tasks` bookkeeping for this endpoint are removed (other task-id endpoints, e.g. image generation, are untouched)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes; a real 1024² render shows the bar moving end to end
