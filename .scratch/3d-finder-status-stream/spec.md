# 3D File Finder — Live Status Stream

## Context

The 3D file finder wizard (`frontend/src/components/ThreeDFileFinder.tsx`, rendered in the Testing tab) runs three steps as blocking fetches with only button spinners: fetch eBay photos, reverse image search, download the 3D file. The user gets no feedback about what is happening. This spec adds a live, non-technical status stream to all three steps, reusing the streaming machinery the repo already has.

## Confirmed design decisions (from grilling session — do not relitigate)

1. **Transport: NDJSON over fetch** — reuse the existing helpers `progress_event` / `result_event` / `error_event` / `streaming_response` (`app.py:188-210`) and the frontend consumer `fetchWithProgress` (`frontend/src/utils/fetchWithProgress.ts:18`). No SSE, no WebSocket, no polling. New status emission is built as reusable functions *within* this existing code — no parallel path.
2. **Message content: non-technical, user-facing text.** "Unzipping files...", "Preparing your download...", never log jargon. Technical detail stays in server-side print/stdout logs.
3. **Numeric progress only when the data source provides real counts.** External APIs that return opaque single responses (SerpAPI) get phase messages only, no progress bar. This rule applies to any outside API.
4. **Step 1 (photos)**: `/api/photos/<listing_id>` already streams progress events; the wizard currently discards them. Switch the wizard to `fetchWithProgress`. Shared messages stay as-is (they are shown in other flows and read fine).
5. **Step 2 (reverse image search)**: `/api/serp-lens` becomes a streaming endpoint emitting friendly phase events ("Searching for 3D files online...", "Checking results across your enabled sites..."). Single SerpAPI call — phases only.
6. **Step 3 (download)**: the five site downloaders (`backend/downloaders/thingiverse.py`, `printables.py`, `makerworld.py`, `cults3d.py`, `thangs.py`) gain an optional `progress_cb` parameter (defaults `None`, existing callers unaffected) emitting friendly per-file events. `/api/download-3d-file` streams these events.
7. **Two-phase file delivery**: the download stream's `result` event carries a `download_id`; bytes are held in a module-level dict (with a lock) and delivered by a new `GET /api/download-3d-file-result/<id>` attachment endpoint. Bytes are deleted from memory once fetched; a stale/unknown ID returns a friendly 404 JSON error. Both Step 3 modes (`single_file`, `files`) use the same stream and delivery path; client-side JSZip handling is unchanged.
8. **UI**: each wizard step gets a compact inline status area inside its own card — one current-activity line, plus a thin progress bar only when counts exist. Errors appear inline in red and as a toast (existing `addToast`). Presentation otherwise left to reasonable judgment for the space; reuse `ProgressIndicator.tsx` where it fits.
9. **Failure semantics**: mid-stream failure ends the stream with an `error` event carrying friendly text (e.g. "Thingiverse didn't respond — try again in a moment"); the step resets so the user can retry. Page refresh aborts the operation — no reconnection machinery.
10. **Convention doc**: `CLAUDE.md` gains a short note — long-running endpoints stream NDJSON progress via the shared helpers; frontends consume via `fetchWithProgress`; messages are non-technical user-facing text; numeric progress only when the data source provides real counts.
11. **Scope**: design generic so other pipelines (eBay downloaders, listing generation) can adopt later; only the 3D file finder is instrumented now.

## Key codebase facts (from exploration)

- Flask backend, dev server threaded (`app.py:4016`); Vite proxies `/api` → `:5000`.
- Existing streaming endpoints for reference: `/api/photos` (`app.py:371`), `/api/create-listing` (`app.py:975`), `/api/remove-backgrounds-batch` (`app.py:3346`).
- Step 3 route `/api/download-3d-file` at `app.py:3149` currently buffers the whole zip and returns raw bytes with `Content-Disposition: attachment` (`app.py:3226-3239`). Downloader dispatch per site: `extract_*` then `stream_zip`/`build_zip`/`download_3mf`; each returns `(filename, raw_bytes)`.
- `mode="single_file"` runs `extract_best_3d_file(zip_bytes)` (`backend/downloaders/zip_utils.py:7`).
- `ThreeDFileFinder.tsx`: `handleStep1Submit` (:131), `handleStep2Search` (:162), `handleStep3Download` (:198); props include `addToast`, `fileDownloadDelay`, `siteStatus`, `enabledSites`.
- `fetchWithProgress(url, options, onProgress)` dispatches `{type: "progress"|"result"|"error"}`; used in `App.tsx` (5 call sites) as reference usage.
- Background-thread + task-id pattern exists (`/api/generate-images`, `app.py:619-678`) but is NOT to be used here — in-request streaming only.

## Assumptions (implementation-level, pre-approved)

- The shared `progress_event` helper may gain optional fields (e.g. `message`, `current`/`total`) — must stay backwards compatible with existing emitters/consumers.
- A stale `download_id` GET returns 404 with friendly JSON.
- Step 1's existing messages are not reworded.

## Verification

- Backend: `python -m pytest tests/` from repo root (use the repo `.venv`).
- Frontend: `cd frontend && npm run build` (tsc + vite) must pass.
- Manual: run the wizard end-to-end against a real listing; each step shows live status; the downloaded file still saves in both modes.
