# History Tab: Pending & Incomplete Visibility Filters

**Date:** 2026-07-12

## Summary

Split the existing single "Show incomplete history" checkbox in the History tab's Filter dropdown into two distinct checkboxes — one for **pending** listings and one for **incomplete** listings — both hidden by default.

## Definitions

| State | Condition | Default visibility |
|-------|-----------|-------------------|
| **Live** | `listing.ebayListingId` is a non-empty string | Always shown |
| **Pending** | No `ebayListingId`, but `isIncomplete()` returns false | Hidden by default |
| **Incomplete** | `isIncomplete()` returns true (placeholder title or no images+placeholder desc) | Hidden by default |

`isIncomplete()` logic in `frontend/src/utils/listingStatus.js` is unchanged.

## Filter Dropdown Changes (`UploadListingsToolbar`)

Replace the existing single `showIncompleteListings` checkbox under the **Visibility** section with two checkboxes:

```
Visibility
[ ] Show pending listings      — real content, not yet uploaded to eBay
[ ] Show incomplete listings   — placeholder/broken drafts
```

- Both default to unchecked (hidden).
- The filter-active dot indicator on the Filter button lights up when either is checked.
- Props added: `showPendingListings` (bool) + `onShowPendingListingsChange` (fn).
- Existing `showIncompleteListings` / `onShowIncompleteListingsChange` props kept as-is.

## Filter Logic Changes (`App.jsx` — `filteredUploadListings` useMemo)

Current logic (single flag):
```js
if (!uploadListingsShowIncomplete && isIncomplete(l)) return false;
```

New logic (two flags):
```js
const hasLiveLink = Boolean(String(listing.ebayListingId ?? "").trim());
if (hasLiveLink) return true; // live listings always shown (rest of filters still apply below)
if (isIncomplete(l) && !uploadListingsShowIncomplete) return false;
if (!isIncomplete(l) && !uploadListingsShowPending) return false;
```

State additions in `App.jsx`:
- `uploadListingsShowPending` — `useState(false)`
- `setUploadListingsShowPending` — passed to `UploadListingsToolbar`

The `filtersActive` expression in `UploadListingsToolbar` also includes `showPendingListings`.

The sort logic (incomplete rows sink to bottom when either show-flag is on) is extended to cover pending rows in the same way.

## Files Changed

- `frontend/src/components/UploadListingsToolbar.jsx` — add `showPendingListings` prop + second checkbox, update `filtersActive`
- `frontend/src/App.jsx` — add `uploadListingsShowPending` state, pass prop, update filter useMemo and sort logic, add to `useEffect` deps
