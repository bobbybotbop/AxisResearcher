# 07: Title-simplification placeholder + prompt hook

**What to build:** A placeholder title-simplification step (deterministic trim of sales terms) wired behind a single swappable function in the Copy Seller pipeline, so when the real prompt arrives (backlog ticket 01) it drops in without touching the pipeline. The simplification is editable in the Testing tab.

**Blocked by:** 03

**Status:** resolved

- [ ] Title simplification lives behind a single swappable function
- [ ] Placeholder deterministically trims sales terms to produce a short search phrase
- [ ] The simplification behavior is editable in the Testing tab
- [ ] The real prompt can be linked later without changing pipeline code (see ticket 01)
