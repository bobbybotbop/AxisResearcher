# 06: Title Search pipeline UI (Steps 1-4 in Testing tab)

**What to build:** New expandable "Title Search" section in the Testing tab (open by default). Step 1: paste eBay link → fetch title + photos (reuses existing `/api/photos/<id>` endpoint). Step 2: show original title → send to Claude Haiku for optimization (strip sales terms like quantity, color, condition) → show optimized title in editable text field → append " 3d file" → "Search" button → call `/api/serp-text-search` → show whitelisted results ordered by site priority. The Haiku prompt is visible in a collapsible section (collapsed by default) and editable. The max results limit (default 35) is an editable number input. Step 3: auto-select top-priority link → run image confirmation in background → show match label ("Confirmed image match" or "Unconfirmed title match"). Step 4: "Use this link →" button forwards the link to the shared download step.

**Blocked by:** 03 (draggable site priority), 04 (site image scrapers), 05 (serp text search)

**Status:** done

- [ ] "Title Search" expandable section exists in Testing tab, open by default
- [ ] Step 1 fetches eBay listing title and photos from pasted link
- [ ] Step 2 shows original title, Haiku-optimized title (editable), and search results
- [ ] Haiku prompt is visible in a collapsed section and editable
- [ ] Max results limit is an editable number input (default 35)
- [ ] Step 3 auto-selects top-priority link and shows match label
- [ ] Step 4 forwards the link to shared download step
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
