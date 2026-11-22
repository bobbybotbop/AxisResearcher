# 08: Testing tab restructure (expandable pipelines + shared Steps 3-4)

**What to build:** Restructure the Testing tab layout: (1) Generic function tester at top (existing, unchanged), (2) "Image Search" expandable section (collapsed by default) containing the current Steps 1-2 (fetch eBay photos, reverse image search), (3) "Title Search" expandable section (open by default) containing the new pipeline from ticket 06, (4) Shared Steps 3-4 (Download + Studio Render) always visible below both pipelines. Both pipelines feed their result link into the shared download step. Each pipeline section has an independent expand/collapse toggle.

**Blocked by:** 06 (Title Search pipeline UI)

**Status:** done

- [ ] Testing tab shows: function tester, Image Search (collapsed), Title Search (open), shared Steps 3-4
- [ ] Image Search section contains only Steps 1-2 (fetch photos + reverse image search)
- [ ] Both pipelines forward their result link to the shared Step 3 download
- [ ] Each pipeline section has an independent expand/collapse toggle
- [ ] Shared Steps 3-4 are always visible regardless of pipeline collapse state
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
