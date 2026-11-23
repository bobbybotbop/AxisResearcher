# 02: Filter blacklisted results server-side in the Image Search Pipeline

**What to build:** When a user runs a reverse image search (`/api/serp-lens`), results from blacklisted sites (marketplaces + Reddit) are dropped by the backend before the response is returned, so the frontend never sees them. Reverse image search has no query string, so server-side post-filtering is the only enforcement possible. Whitelisted and neutral results are returned labeled as before; the frontend continues keeping whitelisted results only, unchanged.

**Blocked by:** 01 (Switch text search to Google Light engine with query-level blacklist exclusions) — needs the Reddit addition to the blacklist constant so image results from Reddit are filtered too.

**Status:** done

- [ ] `/api/serp-lens` response contains no results classified as blacklisted
- [ ] Whitelisted and neutral results are still returned with their `site_type` labels, ordered by site priority as before
- [ ] Image-search endpoint tests updated to assert blacklisted results are absent
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
