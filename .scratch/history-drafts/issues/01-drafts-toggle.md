# 01: Merge incomplete/unuploaded/inactive into one "Show drafts" toggle

**What to build:** On the History tab, the three filters "Show incomplete history", "Show unuploaded listings", and "Show inactive listings" are replaced by a single "Show drafts" toggle (default OFF). A draft is any listing that is incomplete (missing title/images/price/categoryId per the existing completeness check), has never been uploaded (no eBay listing ID), or has `ebay_status: "not_found"` without an eBay listing ID. When shown, drafts render grayed out (existing `opacity-50` treatment, currently used only for inactive). Non-draft listings are unaffected.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] Toolbar shows one "Show drafts" toggle instead of the three old checkboxes
- [ ] Drafts hidden by default; enabling the toggle reveals them grayed out
- [ ] A listing that is complete AND has an eBay listing ID AND is active is never a draft
- [ ] The three old filter state variables and their localStorage keys are removed or migrated
