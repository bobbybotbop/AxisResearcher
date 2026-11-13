# 01: Step status UI + shared streaming helpers, wired into Step 1

**What to build:** A reusable per-step status component for the 3D file finder wizard — a compact inline area showing one current-activity line, a thin progress bar only when event counts exist, and errors inline in red plus a toast. The shared backend `progress_event` helper gains optional friendly-message and count fields without breaking any existing emitter or consumer. Step 1 (fetch eBay photos) switches from plain `fetch` to `fetchWithProgress`, so the user sees the live status the endpoint already streams instead of just a button spinner.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] `progress_event` accepts optional message/count fields; all existing streaming endpoints and frontend consumers behave exactly as before
- [ ] A reusable step-status component exists that any wizard step can render
- [ ] Step 1 shows the live current-activity line while photos are fetched
- [ ] A Step 1 failure shows friendly text inline in red and a toast, and the step can be retried
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
