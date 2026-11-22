# 03: Record the Blacklisted Site term in the glossary

**What to build:** `GLOSSARY.md` gains a **Blacklisted Site** entry: a domain excluded from search queries (via `-site:` clauses in text search) and filtered server-side from all search results; currently marketplaces (ebay, amazon, walmart, etsy, aliexpress, temu, mercari, poshmark) plus reddit. The **Title Search Pipeline** entry is updated to say the text search uses the Google Light engine with blacklist exclusions in the query. The **Image Search Pipeline** entry is updated to say blacklisted results are filtered server-side. The glossary stays free of implementation detail beyond what the terms require.

**Blocked by:** 01 (Switch text search to Google Light engine with query-level blacklist exclusions) — the term's definition includes Reddit and the query-level exclusion behavior, both introduced by ticket 01.

**Status:** ready-for-agent

- [ ] `GLOSSARY.md` defines **Blacklisted Site** consistent with the existing **Whitelisted Site** vocabulary
- [ ] **Title Search Pipeline** entry mentions Google Light engine and query-level blacklist exclusion
- [ ] **Image Search Pipeline** entry mentions server-side blacklist filtering
- [ ] No implementation details beyond what the domain terms require
