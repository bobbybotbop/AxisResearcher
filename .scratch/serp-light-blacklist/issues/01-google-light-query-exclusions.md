# 01: Switch text search to Google Light engine with query-level blacklist exclusions

**What to build:** When a user runs the Title Search Pipeline, the backend sends the query to SerpApi's Google Light engine (`google_light`) instead of the full Google engine, with `-site:` clauses for every blacklisted domain appended automatically to the query. Reddit is added to the blacklist (now: ebay, amazon, walmart, etsy, aliexpress, temu, mercari, poshmark, reddit). Blacklisted results are also filtered server-side from the response as defense in depth, in case Google ignores an exclusion operator. The `max_results` parameter is removed from the endpoint and search function since Google Light does not support `num`. Whitelisted and neutral results are still returned labeled as before, so the frontend needs no changes.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] `BLACKLISTED_SITES` includes `reddit.com`
- [ ] Text search uses the `google_light` engine
- [ ] Query sent to SerpApi has `-site:<domain>` appended for every blacklisted domain, built from the blacklist constant
- [ ] No `num`/`max_results` parameter is sent or accepted for text search
- [ ] Blacklisted results are filtered server-side from the `/api/serp-text-search` response
- [ ] Whitelisted and neutral results are still returned with their `site_type` labels
- [ ] Existing text-search tests updated to assert the new engine, query exclusions, Reddit classification, and server-side filtering
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
