# History Tab: Compact View Mode

**Date:** 2026-07-26

## Overview

Add a compact view mode to the History tab that becomes the new default. Compact mode renders each listing as a short, full-width row — no description panel, no thumbnail strip, reduced height — so more listings are visible at once. A toggle button in the toolbar switches between compact and the existing full-card ("detailed") mode. The per-card click behavior (opens detail modal) is unchanged in both modes.

---

## View Modes

### Compact (new default)

Each listing renders as a single horizontal row with a fixed-height image column on the left:

- **Hero image retained** — the left image column is kept but at a fixed, reduced height (e.g. `h-24` / 96px) instead of the full `aspect-square`. The upload/view button below the image is retained.
- **No description panel** — the scrollable description box is hidden entirely
- **No thumbnail strip** — the `RestGalleryStrip` is not rendered
- **Content column**: title (truncated to one line), meta row (SKU, date, price, image count, category) in the same token style as the existing meta row
- **Full width** — the row spans the full card width, consistent with the existing `w-full` card style
- **Rounded card** with the same `border border-border-default bg-surface-panel shadow-sm` styling and `cursor-pointer hover:shadow-md` behavior as the current card

### Detailed (existing, previously default)

No changes to this mode. Renders `GeneratedListingCard` exactly as it exists today.

---

## Toggle Button

A new icon button is added to `UploadListingsToolbar`, placed to the right of the Filter button and to the left of the Auto-restock group:

- **Size / shape**: `h-10 w-10 rounded-lg border border-border-default bg-surface-panel shadow-sm hover:bg-surface-hover` — identical to the Filter button
- **Icon (compact mode active)**: `LayoutList` from `lucide-react` (rows/list icon)
- **Icon (detailed mode active)**: `LayoutGrid` from `lucide-react` (card/grid icon) — to indicate that clicking switches to detailed
- **Active state**: when compact is active, the button gets a subtle filled background (`bg-surface-hover` or `bg-surface-muted`) so the user can see which mode is current
- **Tooltip / aria-label**: "Switch to detailed view" or "Switch to compact view" depending on current mode

---

## State

A single state variable `historyViewMode` (`"compact" | "detailed"`) is added to `App.jsx`, initialized from `localStorage` (key `axisHistoryViewMode`) so the user's choice persists across sessions. Default: `"compact"`.

Persistence logic:
- On change, write to `localStorage`
- On mount (or via the `useState` initializer), read from `localStorage` and fall back to `"compact"` if absent or invalid

`historyViewMode` is passed as a prop to `UploadListingsToolbar` (for the active-state indicator on the button) and used at the `paginatedListings.map` call site to conditionally render `GeneratedListingCard` (detailed) or the new `CompactListingRow` component (compact).

---

## New Component: `CompactListingRow`

**File**: `frontend/src/components/CompactListingRow.jsx`

**Props** (same subset as `GeneratedListingCard` that are relevant):

```
listing, onCardClick, onUpload, isUploading, uploadResult, quantity, loadingQuantity
```

**Layout** (horizontal `flex md:flex-row` matching the existing card structure):

```
[ image column: fixed h-24 hero + upload button ] | [ content column: title + meta ]
```

- **Image column**: same `w-[30%] max-w-md` left column as the current card, but with `h-24` (96px) fixed height instead of `aspect-square`. Hero image renders `object-contain` within this fixed height. The upload/view button panel beneath is retained unchanged.
- **Title**: `font-semibold text-base leading-snug line-clamp-1 text-text-primary`
- **Meta row** (`text-sm text-text-muted`): SKU, date, price, image count, category — same format helpers already used in `GeneratedListingCard` (`formatListingDateTime`, `formatCategoryShort`, `formatPrice`)
- **Outer wrapper**: `role="button"` with same keyboard (`Enter`/`Space`) and click handling as `GeneratedListingCard`

**No description panel. No thumbnail strip (`RestGalleryStrip` not rendered).**

---

## Toolbar Changes (`UploadListingsToolbar`)

New props added:

```
viewMode,           // "compact" | "detailed"
onViewModeChange,   // (mode) => void
```

The view mode toggle button is inserted between the Filter button and the Auto-restock group. Icon and active-state styling derived from `viewMode` prop.

---

## App.jsx Changes

1. Add `historyViewMode` state (localStorage-persisted, default `"compact"`)
2. Pass `viewMode={historyViewMode}` and `onViewModeChange={setHistoryViewMode}` to `UploadListingsToolbar`
3. At the `paginatedListings.map` call site, branch on `historyViewMode`:
   - `"compact"` → render `CompactListingRow`
   - `"detailed"` → render `GeneratedListingCard` (unchanged)
4. Import `CompactListingRow`

---

## Out of Scope

- No changes to pagination, filtering, sorting, or the detail modal
- No changes to the test workflow tab or mock data
- No grid/column layout — compact mode is still a single-column list, just shorter rows
- No server-side changes
