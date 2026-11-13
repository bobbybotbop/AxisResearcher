# 04: Stream Step 3 download + two-phase file delivery, Thingiverse first

**What to build:** The download step of the 3D file finder shows live, friendly status while a file is fetched — e.g. "Connecting to Thingiverse...", "Downloading file 3 of 12...", "Unzipping files...", "Preparing your download...". The `/api/download-3d-file` route becomes a streaming NDJSON endpoint. Because binary bytes cannot be mixed into the stream, the final `result` event carries a `download_id`; the bytes are held in a module-level dict under a lock, and a new attachment endpoint serves them once, then deletes them. A stale or unknown `download_id` returns a friendly 404 JSON error. `backend/downloaders/thingiverse.py` gains the optional `progress_cb` parameter as the proof site; other sites still work, emitting phase-level events only. Both download modes (`single_file`, `files`) keep working with unchanged client-side file handling.

**Blocked by:** 01 (Step status UI + shared streaming helpers)

**Status:** done

- [ ] `/api/download-3d-file` streams friendly progress events for all five sites (phase-level for sites without a progress callback yet)
- [ ] Thingiverse downloads emit real per-file counts ("Downloading file N of M...")
- [ ] The stream's `result` event carries a `download_id`; the new GET endpoint delivers the bytes as an attachment exactly once, then forgets them
- [ ] A stale/unknown `download_id` returns 404 with a friendly JSON message
- [ ] A mid-download failure ends the stream with a friendly `error` event; the step resets for retry; technical detail stays in server logs
- [ ] Both `single_file` and `files` modes deliver the file to the user exactly as before
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
