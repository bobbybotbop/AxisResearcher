# 3D File Finder — Independent Step Panels

**Date:** 2026-10-07
**File:** `frontend/src/components/ThreeDFileFinder.tsx`

## Problem

The current ThreeDFileFinder forces a single linear path: eBay URL -> photo selection -> SERP search -> download. You cannot test any step in isolation. If you already have an image URL or a printables link, you still have to run the entire flow from the top.

## Goal

Restructure ThreeDFileFinder into three independently operable panels. Each panel has its own input and can be triggered without the others having run. Results from one panel can optionally pre-fill the next panel's input with one click, keeping the full end-to-end flow convenient.

## Layout

Three stacked cards, always visible, within the existing Testing tab location.

```
┌─────────────────────────────────────────────────────┐
│  Step 1 — Fetch eBay Photos                         │
│  [eBay URL or item ID]              [Fetch Photos]  │
│  ─────────────────────────────────────────────────  │
│  "Nike Shoes — 8 photos found"                      │
│  [ img ][ img ][*img*][ img ][ img ]                │
│                         [Use photo in Step 2 →]     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Step 2 — Reverse Image Search                      │
│  [Image URL]                        [Search]        │
│  [ small thumbnail preview ]                        │
│  ─────────────────────────────────────────────────  │
│  Results (4)                                        │
│  1. [ thumb ] printables.com/...            [Use →] │
│  2. [ thumb ] thingiverse.com/...           [Use →] │
│  3. [ thumb ] makerworld.com/...                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Step 3 — Download 3D File                          │
│  [3D site URL]                     [Download]       │
│  "Supported: printables.com, thingiverse.com"       │
│  ─────────────────────────────────────────────────  │
│  ✓ Downloaded: nike-shoe.zip (2.4 MB)               │
└─────────────────────────────────────────────────────┘
```

## Step 1 — Fetch eBay Photos

**Input:** eBay listing URL or item ID text field + "Fetch Photos" button.

**Action:** POST to `/api/photos/<id>?classify=false`. Same call as today.

**Output:** Photo grid below the input. Shows listing title + photo count. Photos are selectable (ring highlight on selected). Only one photo can be selected at a time; first photo is pre-selected on load.

**Forward affordance:** A "Use photo in Step 2 →" button appears below the photo grid, right-aligned, once a photo is selected. It is absent (not disabled) when no photo is selected. Clicking it writes the selected photo URL into Step 2's image URL input. It does not trigger Step 2's search automatically.

**State:**
- `step1Link` — current input value
- `step1Photos` — fetched photo URLs
- `step1Title` — listing title
- `step1Loading` — fetch in flight
- `step1Selected` — currently selected photo URL

## Step 2 — Reverse Image Search

**Input:** Image URL text field + "Search" button. Pre-fillable from Step 1 but fully editable.

**Thumbnail preview:** When the input contains a non-empty string, render a small `<img>` (32x32, `object-cover`, rounded) beside the input so the user can confirm the image before searching. The `<img>` has `onError` that hides it if the URL is not a valid image.

**Action:** POST to `/api/serp-lens` with `{ image_url }`. Filters results to `site_type === "whitelisted"` only (same as today).

**Output:** Numbered result list. Each row shows: thumbnail, title/link, site badge. A "Use →" button appears only on rows where the site has a downloader (`printables.com/model/...` or `thingiverse.com/thing:...` regex match). Clicking "Use →" writes that result's URL into Step 3's URL input. It does not trigger Step 3's download automatically.

Non-downloadable whitelisted sites (makerworld, yeggi, cults3d, myminifactory, thangs) appear in the list with their green "3D site" badge but no button.

**State:**
- `step2ImageUrl` — current input value
- `step2Results` — search results
- `step2Loading` — search in flight

## Step 3 — Download 3D File

**Input:** 3D site URL text field + "Download" button. Pre-fillable from Step 2 but fully editable.

**Validation (inline, not toast):** Below the input, a small helper line reads "Supported: printables.com, thingiverse.com". If the current URL value is non-empty but matches neither supported pattern, replace that line with "Unsupported site" in muted/warning text. The Download button is disabled when the URL is empty or unsupported.

**Action:** POST to `/api/download-3d-file` with `{ link }`. Same backend call as today.

**Output:** Inline success line showing filename and byte size (e.g. "Downloaded: nike-shoe.zip (2.4 MB)"). Replaces any previous result on each new download. On error, shows inline error text in a warning color. No toasts for success or error in Step 3 — everything is shown inline so results persist for inspection.

**State:**
- `step3Url` — current input value
- `step3Loading` — download in flight
- `step3Result` — `{ filename: string; bytes: number } | null`
- `step3Error` — `string | null`

## Data Flow Between Steps

Pre-fills are one-way writes triggered by explicit button clicks. They never auto-trigger the destination step's action.

```
Step 1 selected photo  --[Use photo in Step 2 →]--> step2ImageUrl
Step 2 result URL      --[Use →]-------------------> step3Url
```

## Styling

Each panel is a card using `bg-surface-panel border border-border-default rounded-xl p-4` (matching existing panel styling in the app). The three cards are separated by `gap-4` in a `flex flex-col` container.

Panel headers use the existing `text-lg font-semibold text-text-primary` pattern with a muted step number prefix (e.g. "Step 1 —").

All buttons use existing `btnPill` / `btnPillSm` classes. Loading states use the same `"Loading..."` / `"Searching..."` / `"Downloading..."` patterns as today.

## Component Structure

All changes are contained within `frontend/src/components/ThreeDFileFinder.tsx`. No new files. State is consolidated at the top of the component; the three panels are rendered sequentially in the JSX. The `fetchWithProgress` import can be removed since Step 1 no longer needs it (the photos endpoint returns a simple JSON response, not an NDJSON stream — the current code uses `fetchWithProgress` but does not use the progress callback, so a plain `fetch` is correct).

## Out of Scope

- No changes to backend endpoints.
- No changes to App.tsx (ThreeDFileFinder is already embedded in the Testing tab; its props stay the same).
- No changes to how the Testing tab's other controls (the `/api/testing` run button) work.
