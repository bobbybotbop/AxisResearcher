# Original Photos — Select Mode & Bulk Actions

**Date:** 2026-07-13  
**Status:** Approved

## Context

The Original Photos section in the Create tab has an Image Editor button and an Upload Images button, but no way to select multiple images for bulk operations. The request is to add a Select mode toggle and a Bulk Actions dropdown (currently only Skip) to the header button row, keeping selection logic self-contained inside `PhotoGallery.jsx`.

The per-image `<select>` category dropdown at the bottom of each tile is `absolute bottom-0` and was being confused with a "select button" — no change needed there, it remains as-is.

## Scope

Single file change: `frontend/src/components/PhotoGallery.jsx`.

## Design

### Header Button Row

Current: `[Image Editor] [Upload Images]`  
New:     `[Image Editor] [Upload Images] [Select] [Bulk Actions ▾]`

### Select Button

- Toggles `selectMode` bool state (local to `PhotoGallery`)
- When `selectMode` is true, button label changes to **"Done"** (or active visual style) to signal the mode
- Pressing it again exits select mode and clears all selections

### Bulk Actions Button

- Opens a small dropdown with one item: **Skip**
- Disabled (grayed out) when `selectedPhotos` is empty or `selectMode` is false
- After Skip runs: exits select mode, clears selection

### New Local State

```
selectMode: bool         — whether image clicks select rather than open lightbox
selectedPhotos: Set<int> — indices of currently selected images
dropdownOpen: bool       — controls Bulk Actions dropdown visibility
```

### Select Mode — On

- Clicking an image toggles its index in `selectedPhotos`
- Selected images show: colored ring border + checkmark overlay in a corner
- Lightbox does NOT open on click
- Per-image hover skip button is hidden (prevent accidental single-skip during bulk workflow)

### Select Mode — Off (default)

- Clicking an image opens the Lightbox (existing behavior, unchanged)
- Per-image hover skip button visible as before
- `selectedPhotos` is empty

### Bulk Actions — Skip

1. For each index in `selectedPhotos`: call `onSkipPhoto(index)` (existing prop, already skips images)
2. Exit select mode, clear `selectedPhotos`

No new props required.

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/PhotoGallery.jsx` | Add `selectMode`, `selectedPhotos`, `dropdownOpen` state; add Select + Bulk Actions buttons to header; wire image onClick for selection; add selection highlight overlay; hide per-image skip button in select mode; add dropdown |

No changes to `App.jsx`, `CreateWorkflow.jsx`, or any other file.

## Verification

1. Run `npm run dev` and open the Create tab
2. Confirm header shows: Image Editor, Upload Images, Select, Bulk Actions (grayed)
3. Click **Select** → button changes to "Done", Bulk Actions still grayed (nothing selected)
4. Click images → each gets ring + checkmark; Bulk Actions becomes enabled
5. Click **Bulk Actions → Skip** → selected images marked as skipped, mode exits, selection clears
6. Click **Done** without skipping → mode exits cleanly, images unaffected
7. Confirm clicking images outside select mode still opens Lightbox
8. Confirm category `<select>` dropdowns still work normally on all images
