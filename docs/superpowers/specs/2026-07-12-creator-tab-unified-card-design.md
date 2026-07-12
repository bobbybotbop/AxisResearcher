# Creator Tab — Unified Listing Card

**Date:** 2026-07-12  
**Status:** Approved

## Goal

Collapse the two-panel layout (top `ListingDetails` + bottom "Generated Listing" section) in the Create tab into a single unified card. The generated title and description are the primary content; the original values are accessible on demand via a disclosure toggle.

---

## What changes

### Files modified
- `frontend/src/components/CreateWorkflow.jsx` — remove `<ListingDetails>` usage, add metadata row and disclosure to the generated listing block; add `showOriginal` local state
- `frontend/src/utils/listingDisplay.js` — update `formatListingDateTime` to output `MM/DD/YYYY, HH:MM`

### Files deleted
- `frontend/src/components/ListingDetails.jsx` — no longer used anywhere

### Files NOT changed
- `frontend/src/App.jsx` — no state changes needed; all required data already flows into `CreateWorkflow` as props
- `frontend/src/components/MessageBarInput.jsx`
- `frontend/src/utils/listingDisplay.js` (other exports)

---

## Unified card layout

Rendered when `listingLinkSubmitted && listing`. Replaces both the old `<ListingDetails>` block and the old "Generated Listing" heading block.

```
┌──────────────────────────────────────────────────────────────────┐
│  [SKU-0042]  [07/11/2026, 14:43]  [3 images]  [Cat 9355]  $24.99 │
│  ──────────────────────────────────────────────────────────────  │
│  [Title input — editable, locked while isGeneratingText]         │
│  char counter · AI Trim · Save Title  (hidden while generating)  │
│  ──────────────────────────────────────────────────────────────  │
│  [Description textarea — Edit HTML / Preview HTML toggle]        │
│  Save Description  (hidden while generating)                     │
│  ──────────────────────────────────────────────────────────────  │
│  ▶ View original title and description                           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Metadata row

```
[SKU-0042]  [07/11/2026, 14:43]  [3 images]  [Cat 9355]          $24.99
```

| Field | Source | Notes |
|---|---|---|
| SKU | `currentSku` | `font-mono` badge |
| Date | `formatListingDateTime(listing.itemCreationDate)` | format: `MM/DD/YYYY, HH:MM` |
| Image count | `generatedImages.length` | live — updates as user adds/removes images |
| Category | `formatCategoryShort(listing.categoryId)` prefixed `Cat ` | badge |
| Price | `formatPrice(listing.price, listing.currency)` | right-aligned, plain `text-xl font-bold`, NOT a badge, NOT duplicated |

**Badge style:** `border border-border-default rounded-md px-2 py-0.5 text-xs text-text-muted` — one per field, no dot separators.

---

## Title field

- Input bound to `editableTitle`
- `disabled={isGeneratingText}` — muted visual (`opacity-60 cursor-not-allowed`) while streaming; text still appears live
- Char counter badges (>80 red / 73–80 green / <73 blue) always visible once text present
- "AI Trim" and "Save Title" buttons: `hidden` while `isGeneratingText`, visible once complete

---

## Description field

- `descriptionEditMode` local toggle (already exists) between "Edit HTML" and "Preview HTML"
- `<textarea>` bound to `editableDescription`
- `disabled={isGeneratingText}` — same muted visual while streaming
- "Save Description" button: hidden while `isGeneratingText`, visible once complete

---

## "View original" disclosure

**New local state:** `showOriginal` (boolean, default `false`) in `CreateWorkflow.jsx`.  
**Reset:** set to `false` whenever `listingLinkSubmitted` transitions to `false`.

Toggle button below description field:
- Closed: `▶ View original title and description`
- Open: `▼ Hide original title and description`
- Style: plain text button, `text-sm text-text-muted hover:text-text-primary`

Expanded content (read-only):
```
Original title — text-sm font-semibold text-text-primary, no input
Original description — bg-surface-muted rounded-lg border border-border-default p-3
                       whitespace-pre-wrap text-sm text-text-primary
                       max-h ~6 lines + overflow-y-auto (matches current ListingDetails description box)
```

Source: `listing.title` and `listing.description` (the raw fetch object, unchanged).

---

## `formatListingDateTime` update

Current output: `"11 Jul 2026, 14:43"`  
New output: `"07/11/2026, 14:43"`

Change only the date formatting logic in `listingDisplay.js`. Time format (24h, HH:MM) stays the same.

---

## What does NOT change

- All existing "Generated Listing" controls (char counter, AI Trim, Save Title, Edit HTML/Preview HTML, Save Description, Upload to eBay, upload progress, success card)
- Progress indicators (`createListingProgress`)
- `listingData` detail block (SKU, price, category, images, created date from the eBay API object) — stays as-is below the description. Note: this block shows data from the saved eBay draft object (populated after confirm), while the metadata row at the top shows data from the original source listing fetch. They are different data sources and both intentionally present.
- Photo gallery sections above the card
- `MessageBarInput` fixed bottom bar
- Test Workflow tab — mirror any `CreateWorkflow` structural changes in the corresponding `test*` handlers (per CLAUDE.md)
