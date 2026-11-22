# 02: Rename "manually listed" to "imported", always shown, with UI chip

**What to build:** The "Show manually listed items" filter is removed entirely. Listings imported from eBay (currently `isManualListing`) are always visible on the History tab regardless of toggle state, render with normal (non-grayed) appearance, and carry a small "Imported" chip/badge on both card and compact-row views so users can tell they were created outside Axis Researcher.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] No "manually listed" filter remains in the toolbar
- [ ] Imported listings always appear in the list (not grayed out)
- [ ] "Imported" chip renders on both card view and compact row view
