# 05: SerpAPI text search endpoint

**What to build:** New `POST /api/serp-text-search` endpoint accepting `{query, enabled_sites, max_results, site_priorities}`. Uses the existing SerpAPI key (`serp_api_token` env var) with the Google text search engine. Returns up to `max_results` results, each classified against whitelisted/blacklisted sites, filtered by enabled sites, ordered by site priority (from `site_priorities` param). Mirrors the existing `/api/serp-lens` pattern but for text search instead of reverse image search.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] `POST /api/serp-text-search` accepts query, enabled_sites, max_results, site_priorities
- [ ] Uses SerpAPI Google text search engine with existing API key
- [ ] Results are classified (whitelisted/blacklisted/neutral) and filtered by enabled sites
- [ ] Results are ordered by site priority
- [ ] Returns up to max_results (default 35)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
