# 03: Stream Step 2 (reverse image search) status

**What to build:** The reverse-image-search step of the 3D file finder shows live, friendly phase messages while it runs — e.g. "Searching for 3D files online..." then "Checking results across your enabled sites..." — instead of a bare spinner. The `/api/serp-lens` endpoint becomes a streaming NDJSON endpoint using the shared helpers. No progress bar: SerpAPI is one opaque call, so there are no real counts to show. The wizard's Step 2 renders the reusable step-status component from ticket 01. Failures produce a friendly inline error plus toast, and the step can be retried.

**Blocked by:** 01 (Step status UI + shared streaming helpers)

**Status:** done

- [ ] `/api/serp-lens` streams friendly phase events via the shared NDJSON helpers and ends with the existing result payload shape
- [ ] Step 2 in the wizard consumes the stream and shows the current phase live in its inline status area
- [ ] No progress bar is shown for Step 2 (no real counts exist)
- [ ] A failed search shows friendly text inline in red plus a toast, and the step resets for retry
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
