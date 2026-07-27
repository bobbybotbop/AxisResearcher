# Automatic Background Removal — Design Spec

**Date:** 2026-07-26

## Context

When a user submits an eBay listing link, the source photos often have cluttered backgrounds. The image editor already has background removal (rembg via `/api/remove-background`), but it requires manual use. This feature automatically removes backgrounds from all source photos immediately after they load, displays the results in a new section below the originals, and passes the bg-removed versions to AI generation instead of the originals when the user confirms categories. This improves AI output quality since generation models perform better on clean, bg-removed inputs.

The feature is behind a localStorage feature flag defaulting to `true` (auto-enabled).

---

## Backend

### New endpoint: `POST /api/remove-backgrounds-batch`

Request body:
```json
{ "photos": ["https://i.ebayimg.com/...", ...], "sku": "076" }
```

Behavior:
- Streams NDJSON progress events, one per completed image, using the existing `progress_event` / `result_event` / `error_event` / `streaming_response` helpers already used by `/api/create-listing` and `/api/upload-listing`.
- For each URL: downloads the image bytes via `requests.get()`, calls `remove_background(image_bytes)` from `backend.copyScripts.imageEditing`, saves the PNG to `generated-images/bg_removed_{sku}_{idx}.png`.
- Progress event shape (one per image): `{ "type": "progress", "step": "Removing background 1 of N", "status": "in_progress" }`.
- Final result event: `{ "type": "result", "data": { "bgRemovedPhotos": { "<originalUrl>": "/api/bg-removed-image/bg_removed_076_0.png", ... } } }`.
- On any single-image failure: skip that image, do not abort the whole batch. Omit the failed URL from the result map.

### New endpoint: `GET /api/bg-removed-image/<filename>`

Serves PNG files from the `generated-images/` directory. Validates that `filename` matches the pattern `bg_removed_<sku>_<idx>.png` (no path traversal). Returns `image/png`. Returns 404 if not found.

---

## Frontend State

New state in `App.jsx`:

```js
// Feature flag — localStorage, default true
const [autoBackgroundRemovalEnabled, setAutoBackgroundRemovalEnabled] = useState(() => {
  try {
    const stored = localStorage.getItem("axisAutoBackgroundRemoval");
    return stored === null ? true : stored === "true";
  } catch { return true; }
});

// { [originalUrl]: bgRemovedUrl } — populated as batch streams in
const [bgRemovedPhotos, setBgRemovedPhotos] = useState({});

// Progress state — same shape as fetchProgress / createListingProgress
const [bgRemovalProgress, setBgRemovalProgress] = useState({
  isActive: false, currentStep: null, completedSteps: [], totalSteps: []
});
```

Persist the flag to localStorage on change (same `useEffect` pattern as `axisClassifyImagesEnabled`).

---

## Trigger Point

In `fetchListingPhotos` in `App.jsx`, immediately after the auto-skip logic resolves and `setSkippedPhotos()` is called (roughly line 870), add:

```js
if (autoBackgroundRemovalEnabled && data.photos?.length && data.sku) {
  triggerAutoBackgroundRemoval(data.photos, data.sku);
}
```

`triggerAutoBackgroundRemoval(photos, sku)` is a new async function that:
1. Initializes `bgRemovalProgress` with `{ isActive: true, currentStep: null, completedSteps: [], totalSteps: photos.map((_, i) => \`Image ${i + 1}\`) }`.
2. Calls `fetchWithProgress(...)` on `/api/remove-backgrounds-batch` with `{ photos, sku }`.
3. On each progress event: updates `bgRemovalProgress.completedSteps` / `currentStep`.
4. On result: calls `setBgRemovedPhotos(data.bgRemovedPhotos)`, sets `bgRemovalProgress.isActive` to false.
5. On error: sets `bgRemovalProgress.isActive` to false, leaves `bgRemovedPhotos` as-is (empty = fallback to originals).

This runs in parallel with `startTextGeneration()` — no awaiting, no blocking.

---

## UI Layout

In `CreateWorkflow.jsx`, between the existing `PhotoGallery` and the Confirm Categories button:

```
[Source Photos]                  — PhotoGallery, unchanged (hideConfirmButton prop added)
[Background Removal section]     — NEW, shown when autoBackgroundRemovalEnabled
  - Progress bar while active    — same inline green bar style as imageGenProgress
  - "Removing backgrounds... X of N complete"
  - Grid of bg-removed images    — appears as results stream in, same grid style as PhotoGallery
    - No category dropdowns
    - No skip/editor buttons
    - Read-only preview
[Confirm Categories button]      — MOVED here (was inside PhotoGallery)
```

The bg-removed grid grows incrementally as each image streams in — same approach as how `generatedImages` populates the AI output grid.

### Confirm Categories button move

`PhotoGallery.jsx` receives a new prop `hideConfirmButton` (boolean). When true, the footer with the Confirm Categories button is not rendered. `CreateWorkflow.jsx` passes `hideConfirmButton={autoBackgroundRemovalEnabled}` and renders the button itself below the new section.

When `autoBackgroundRemovalEnabled` is false, `hideConfirmButton` is false and the button stays in `PhotoGallery` exactly as today — no regression.

---

## Confirm Categories Integration

In `handleConfirmCategories` in `App.jsx`:

```js
const hasBgRemoved = autoBackgroundRemovalEnabled && Object.keys(bgRemovedPhotos).length > 0;

const photosToSend = hasBgRemoved
  ? photos.map(url => bgRemovedPhotos[url] || url)  // fall back to original if a photo failed
  : photos;

const categoriesToSend = hasBgRemoved
  ? Object.fromEntries(
      Object.entries(editableCategories).map(([origUrl, cat]) => [
        bgRemovedPhotos[origUrl] || origUrl,
        cat
      ])
    )
  : editableCategories;

// Pass photosToSend and categoriesToSend to /api/generate-images instead of photos / editableCategories
```

If bg removal is still in progress (`bgRemovalProgress.isActive`) when the user clicks Confirm Categories, proceed with originals (same fallback as above — `bgRemovedPhotos[url] || url` naturally falls back). No blocking, no modal.

---

## Settings Tab

In the Settings tab in `App.jsx`, add a new toggle block following the exact same markup pattern as the Classify Images toggle:

```jsx
<div className="mb-5 rounded-xl border border-border-default bg-surface-muted p-5">
  <div className="flex items-center justify-between gap-3">
    <div>
      <h3 className="m-0 text-lg font-semibold text-text-primary">
        Auto Background Removal
      </h3>
      <p className="mt-1 text-sm text-text-muted">
        Automatically removes backgrounds from source photos before AI generation. Improves output quality on clean product shots.
      </p>
    </div>
    <button
      type="button"
      className="cursor-pointer rounded-lg border border-border-default bg-surface-panel px-4 py-2 text-sm font-semibold text-text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:bg-surface-hover hover:shadow-md"
      onClick={() => setAutoBackgroundRemovalEnabled(prev => !prev)}
      aria-label="Toggle automatic background removal"
      aria-pressed={autoBackgroundRemovalEnabled}
    >
      {autoBackgroundRemovalEnabled ? "Auto BG Removal: On" : "Auto BG Removal: Off"}
    </button>
  </div>
</div>
```

---

## Test Workflow Mirror

Per CLAUDE.md, the Test Workflow tab must mirror real Create workflow changes. Add to the test flow:

- New `testBgRemovedPhotos` state (same shape as `bgRemovedPhotos`).
- New `testBgRemovalProgress` state.
- New `testTriggerAutoBackgroundRemoval(photos, sku)` that uses `setTimeout` delays (same mock pattern used elsewhere in the test flow) to simulate per-image progress. Populates `testBgRemovedPhotos` with fake local blob URLs or data URIs once "complete."
- The bg-removal section in `CreateWorkflow.jsx` is driven by whichever set of props the parent passes — `isTestMode` prop already threads through, so the test flow passes its own state.

---

## State Reset

In `fetchListingPhotos`, at the reset block near the top (where `setPhotos([])`, `setGeneratedImages([])` etc. are called), also reset:

```js
setBgRemovedPhotos({});
setBgRemovalProgress({ isActive: false, currentStep: null, completedSteps: [], totalSteps: [] });
```

---

## Files Changed

| File | Change |
|------|--------|
| `app.py` | Add `POST /api/remove-backgrounds-batch` and `GET /api/bg-removed-image/<filename>` |
| `frontend/src/App.jsx` | New state, `triggerAutoBackgroundRemoval`, trigger in `fetchListingPhotos`, updated `handleConfirmCategories`, new Settings toggle, reset in fetchListingPhotos |
| `frontend/src/components/CreateWorkflow.jsx` | New bg-removal section, Confirm Categories button hoisted, `hideConfirmButton` prop plumbed |
| `frontend/src/components/PhotoGallery.jsx` | Add `hideConfirmButton` prop |
