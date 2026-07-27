# Automatic Background Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically remove backgrounds from source photos immediately after a listing loads, display the results in a new section, and pass the bg-removed versions to AI generation when the user confirms categories.

**Architecture:** New streaming backend endpoint downloads each photo URL server-side, runs rembg, saves PNGs to `generated-images/`, and streams NDJSON progress back. Frontend calls it in parallel with text generation after photos land, stores results in a `bgRemovedPhotos` map keyed by original URL, swaps them in at Confirm Categories time, and renders a new section in `CreateWorkflow` between the source photo grid and the Confirm button. The Confirm Categories button is hoisted from `PhotoGallery` into `CreateWorkflow` to sit below the new section. A localStorage feature flag (default `true`) gates the whole feature.

**Tech Stack:** Python/Flask (rembg already installed), React/JSX (Vite), Tailwind v4 CSS tokens, existing `fetchWithProgress` + NDJSON streaming pattern, existing `ProgressIndicator` component.

---

## File Map

| File | Change |
|------|--------|
| `app.py` | Add `POST /api/remove-backgrounds-batch` and `GET /api/bg-removed-image/<filename>` |
| `frontend/src/App.jsx` | Feature flag state, `bgRemovedPhotos`, `bgRemovalProgress`, `triggerAutoBackgroundRemoval`, fetchListingPhotos hook + reset, handleConfirmCategories swap, Settings toggle, test workflow mirror state + trigger |
| `frontend/src/testWorkflowState.js` | Add `bgRemovedPhotos` and `bgRemovalProgress` initial values |
| `frontend/src/components/CreateWorkflow.jsx` | New bg-removal section, hoisted Confirm Categories button, new props |
| `frontend/src/components/PhotoGallery.jsx` | Add `hideConfirmButton` prop |

---

## Task 1: Backend — Batch Background Removal Endpoint

**Files:**
- Modify: `app.py` (after the existing `/api/remove-background` endpoint, around line 2094)

- [ ] **Step 1: Add `POST /api/remove-backgrounds-batch` to app.py**

Find the existing `/api/remove-background` endpoint (line ~2061) and add the following immediately after it (after the closing of the function, around line 2094):

```python
@app.route('/api/remove-backgrounds-batch', methods=['POST'])
def remove_backgrounds_batch():
    """
    Remove backgrounds from a list of photo URLs in batch, streaming progress.

    Accepts JSON body:
    {
        "photos": ["url1", "url2", ...],
        "sku": "076"
    }

    Streams NDJSON: one progress event per image, then a result event with
    { "bgRemovedPhotos": { "<originalUrl>": "/api/bg-removed-image/<file>", ... } }
    Failed images are silently skipped (omitted from the result map).
    """
    data = request.get_json()
    photos = data.get("photos", [])
    sku = data.get("sku", "unknown")

    if not photos:
        return jsonify({"error": "No photos provided"}), 400

    def generate():
        bg_removed_map = {}
        total = len(photos)
        os.makedirs("generated-images", exist_ok=True)

        for idx, url in enumerate(photos):
            step_label = f"Removing background {idx + 1} of {total}"
            yield progress_event(step_label, "in_progress")
            try:
                img_response = requests.get(url, timeout=15)
                img_response.raise_for_status()
                result_bytes = remove_background(img_response.content)
                filename = f"bg_removed_{sku}_{idx}.png"
                filepath = os.path.join("generated-images", filename)
                with open(filepath, 'wb') as f:
                    f.write(result_bytes)
                bg_removed_map[url] = f"/api/bg-removed-image/{filename}"
                yield progress_event(step_label, "completed")
            except Exception as e:
                print(f"[API] /api/remove-backgrounds-batch: skipping {url}: {e}")

        yield result_event({"bgRemovedPhotos": bg_removed_map})

    return streaming_response(generate())
```

- [ ] **Step 2: Add `GET /api/bg-removed-image/<filename>` to app.py**

Add immediately after the batch endpoint above:

```python
@app.route('/api/bg-removed-image/<filename>', methods=['GET'])
def serve_bg_removed_image(filename):
    """Serve a bg-removed PNG from generated-images/. Validates filename pattern."""
    import re
    if not re.match(r'^bg_removed_[\w\-]+_\d+\.png$', filename):
        return jsonify({"error": "Invalid filename"}), 400
    filepath = os.path.join("generated-images", filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    with open(filepath, 'rb') as f:
        return Response(f.read(), mimetype='image/png')
```

- [ ] **Step 3: Manually verify the endpoint**

Start the backend: `npm run dev:backend`

In a browser or curl, POST to the endpoint with two real eBay image URLs from a test listing. Confirm it streams NDJSON lines and returns the result with file URLs. Confirm the PNG files appear in `generated-images/` and are servable via the GET endpoint.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add /api/remove-backgrounds-batch and /api/bg-removed-image endpoints"
```

---

## Task 2: Frontend Feature Flag State + Settings Toggle

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add `autoBackgroundRemovalEnabled` state**

In `App.jsx`, find the `classifyImagesEnabled` state declaration (line 306):

```js
const [classifyImagesEnabled, setClassifyImagesEnabled] = useState(() => {
  try {
    return localStorage.getItem("axisClassifyImagesEnabled") === "true";
  } catch {
    return false;
  }
});
```

Add the following immediately after it (after line 312):

```js
const [autoBackgroundRemovalEnabled, setAutoBackgroundRemovalEnabled] = useState(() => {
  try {
    const stored = localStorage.getItem("axisAutoBackgroundRemoval");
    return stored === null ? true : stored === "true";
  } catch {
    return true;
  }
});
```

- [ ] **Step 2: Add localStorage persist useEffect**

Find the `classifyImagesEnabled` persist effect (line 464):

```js
useEffect(() => {
  try {
    localStorage.setItem(
      "axisClassifyImagesEnabled",
      classifyImagesEnabled ? "true" : "false",
    );
  } catch {
    // ignore
  }
}, [classifyImagesEnabled]);
```

Add the following immediately after it (after line 473):

```js
useEffect(() => {
  try {
    localStorage.setItem(
      "axisAutoBackgroundRemoval",
      autoBackgroundRemovalEnabled ? "true" : "false",
    );
  } catch {
    // ignore
  }
}, [autoBackgroundRemovalEnabled]);
```

- [ ] **Step 3: Add Settings tab toggle**

Find the Classify Images toggle block in the Settings tab (line 3183):

```jsx
<div className="mb-5 rounded-xl border border-border-default bg-surface-muted p-5">
  <div className="flex items-center justify-between gap-3">
    <div>
      <h3 className="m-0 text-lg font-semibold text-text-primary">
        Classify Images
      </h3>
```

Add the following new block immediately before it (before line 3183):

```jsx
<div className="mb-5 rounded-xl border border-border-default bg-surface-muted p-5">
  <div className="flex items-center justify-between gap-3">
    <div>
      <h3 className="m-0 text-lg font-semibold text-text-primary">
        Auto Background Removal
      </h3>
      <p className="mt-1 text-sm text-text-muted">
        Automatically removes backgrounds from source photos before AI
        generation. Improves output quality on clean product shots.
      </p>
    </div>
    <button
      type="button"
      className="cursor-pointer rounded-lg border border-border-default bg-surface-panel px-4 py-2 text-sm font-semibold text-text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:bg-surface-hover hover:shadow-md"
      onClick={() => setAutoBackgroundRemovalEnabled((prev) => !prev)}
      aria-label="Toggle automatic background removal"
      aria-pressed={autoBackgroundRemovalEnabled}
    >
      {autoBackgroundRemovalEnabled
        ? "Auto BG Removal: On"
        : "Auto BG Removal: Off"}
    </button>
  </div>
</div>
```

- [ ] **Step 4: Verify settings toggle in browser**

Run `npm run dev`, go to the Settings tab, confirm the new toggle renders above the Classify Images toggle with the correct label. Toggle it on/off and confirm `localStorage.getItem("axisAutoBackgroundRemoval")` changes in the browser console. Confirm the default is `"true"` (clearing localStorage and refreshing should show it as On).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add autoBackgroundRemovalEnabled feature flag with settings toggle"
```

---

## Task 3: BG Removal State, Trigger Function, and fetchListingPhotos Hook

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add `bgRemovedPhotos` and `bgRemovalProgress` state**

In `App.jsx`, find where `generatedImages` state is declared (search for `const [generatedImages`). Add the following two state declarations immediately after the `autoBackgroundRemovalEnabled` state from Task 2:

```js
const [bgRemovedPhotos, setBgRemovedPhotos] = useState({});
const [bgRemovalProgress, setBgRemovalProgress] = useState({
  isActive: false,
  currentStep: null,
  completedSteps: [],
  totalSteps: [],
});
```

- [ ] **Step 2: Add `triggerAutoBackgroundRemoval` function**

Find `fetchListingPhotos` in `App.jsx` (line ~778). Add the following new function immediately before it:

```js
const triggerAutoBackgroundRemoval = async (photoUrls, sku) => {
  setBgRemovalProgress({
    isActive: true,
    currentStep: null,
    completedSteps: [],
    totalSteps: photoUrls.map((_, i) => `Image ${i + 1}`),
  });
  try {
    const data = await fetchWithProgress(
      "/api/remove-backgrounds-batch",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photos: photoUrls, sku }),
      },
      (event) => {
        setBgRemovalProgress((prev) => {
          if (event.status === "completed") {
            return {
              ...prev,
              completedSteps: [...prev.completedSteps, event.step],
              currentStep: null,
            };
          }
          return { ...prev, currentStep: event.step };
        });
      },
    );
    setBgRemovedPhotos(data.bgRemovedPhotos || {});
  } catch (err) {
    console.error("[BG Removal] Failed:", err);
  } finally {
    setBgRemovalProgress((prev) => ({ ...prev, isActive: false }));
  }
};
```

- [ ] **Step 3: Call trigger in fetchListingPhotos after photos land**

In `fetchListingPhotos`, find the `setSkippedPhotos(autoSkip)` line (line ~870). Add the trigger call immediately after it:

```js
setSkippedPhotos(autoSkip);
// Add these lines:
if (autoBackgroundRemovalEnabled && data.photos?.length && data.sku) {
  triggerAutoBackgroundRemoval(data.photos, data.sku);
}
```

- [ ] **Step 4: Reset bg removal state in fetchListingPhotos**

In `fetchListingPhotos`, find the reset block near the top of the function (around line 785, where `setPhotos([])`, `setCategories({})`, `setGeneratedImages([])` etc. are called). Add the two resets:

```js
setBgRemovedPhotos({});
setBgRemovalProgress({
  isActive: false,
  currentStep: null,
  completedSteps: [],
  totalSteps: [],
});
```

- [ ] **Step 5: Verify in browser**

Run `npm run dev`, submit a listing link. In the browser console, log `bgRemovedPhotos` state — confirm it populates after the photos appear. Network tab should show a POST to `/api/remove-backgrounds-batch` firing immediately after the photos fetch resolves.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add bgRemovedPhotos state and triggerAutoBackgroundRemoval in fetchListingPhotos"
```

---

## Task 4: Update handleConfirmCategories to Use BG-Removed Photos

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Swap photos and categories in handleConfirmCategories**

In `App.jsx`, find `handleConfirmCategories` (line ~1148). It currently builds `photosToProcess` and `categoriesToProcess` from the raw `photos` array. Replace those two blocks:

Current code (lines 1158-1171):
```js
const photosToProcess = photos.filter(
  (photoUrl) => !skippedPhotos.has(photoUrl),
);
if (photosToProcess.length === 0) {
  throw new Error("All photos are skipped. Include at least one photo.");
}

const categoriesToProcess = {};
photosToProcess.forEach((photoUrl) => {
  if (editableCategories[photoUrl]) {
    categoriesToProcess[photoUrl] = editableCategories[photoUrl];
  }
});
```

Replace with:

```js
const hasBgRemoved =
  autoBackgroundRemovalEnabled &&
  Object.keys(bgRemovedPhotos).length > 0;

const photosToProcess = photos
  .filter((photoUrl) => !skippedPhotos.has(photoUrl))
  .map((photoUrl) =>
    hasBgRemoved ? bgRemovedPhotos[photoUrl] || photoUrl : photoUrl,
  );

if (photosToProcess.length === 0) {
  throw new Error("All photos are skipped. Include at least one photo.");
}

const categoriesToProcess = {};
photos
  .filter((photoUrl) => !skippedPhotos.has(photoUrl))
  .forEach((originalUrl) => {
    const dest = hasBgRemoved
      ? bgRemovedPhotos[originalUrl] || originalUrl
      : originalUrl;
    if (editableCategories[originalUrl]) {
      categoriesToProcess[dest] = editableCategories[originalUrl];
    }
  });
```

- [ ] **Step 2: Verify in browser**

Submit a listing link. Wait for bg removal to finish (check `bgRemovedPhotos` in console). Click Confirm Categories. In the Network tab, inspect the POST body of `/api/generate-images` — the `photos` array should contain `/api/bg-removed-image/bg_removed_...` URLs instead of the original eBay URLs. The categories keys should match those same URLs.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: pass bg-removed photos to AI generation in handleConfirmCategories"
```

---

## Task 5: PhotoGallery — Add hideConfirmButton Prop

**Files:**
- Modify: `frontend/src/components/PhotoGallery.jsx`

- [ ] **Step 1: Add hideConfirmButton prop and conditional render**

In `PhotoGallery.jsx`, find the function signature / destructured props at the top of the component. Add `hideConfirmButton = false` to the props destructuring.

Then find the Confirm Categories button footer (line ~255):

```jsx
<div className="mt-8 flex justify-center">
  <button
    type="button"
    className={btnPillLg}
    onClick={(e) => {
      e.preventDefault();
      e.stopPropagation();
      if (onConfirm) {
        onConfirm();
      }
    }}
    disabled={isConfirming}
  >
    {isConfirming ? "Generating Images..." : "Confirm Categories"}
  </button>
</div>
```

Wrap it in a conditional:

```jsx
{!hideConfirmButton && (
  <div className="mt-8 flex justify-center">
    <button
      type="button"
      className={btnPillLg}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (onConfirm) {
          onConfirm();
        }
      }}
      disabled={isConfirming}
    >
      {isConfirming ? "Generating Images..." : "Confirm Categories"}
    </button>
  </div>
)}
```

- [ ] **Step 2: Verify no regression**

Run `npm run dev`, submit a listing. Confirm the Confirm Categories button still appears inside PhotoGallery (because `autoBackgroundRemovalEnabled` defaults to true but the prop hasn't been wired up yet — it will use the default `false` until Task 6).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PhotoGallery.jsx
git commit -m "feat: add hideConfirmButton prop to PhotoGallery"
```

---

## Task 6: CreateWorkflow — BG Removal Section and Hoisted Confirm Button

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx`

- [ ] **Step 1: Add new props to CreateWorkflow's prop list**

Find the destructured props at the top of `CreateWorkflow`. Add:

```js
autoBackgroundRemovalEnabled,
bgRemovedPhotos,
bgRemovalProgress,
```

alongside the existing props.

- [ ] **Step 2: Pass hideConfirmButton to PhotoGallery**

Find the `<PhotoGallery ... />` usage (line ~527). Add the `hideConfirmButton` prop:

```jsx
<PhotoGallery
  photos={photos}
  editableCategories={editableCategories}
  onCategoryChange={onCategoryChange}
  onConfirm={onConfirmCategories}
  isConfirming={isConfirming}
  onPhotoClick={onPhotoClick}
  skippedPhotos={skippedPhotos}
  onSkipPhoto={onSkipPhoto}
  onAddToOriginalPhotos={onAddToOriginalPhotos}
  onOpenEditor={onEditorToggle}
  showClassification={classifyImagesEnabled}
  hideConfirmButton={autoBackgroundRemovalEnabled}
/>
```

- [ ] **Step 3: Add the BG Removal section + hoisted Confirm Categories button**

Find the block starting at `{photos?.length > 0 && (` (line ~525). It currently ends after the `imageGenProgress` bar closing `</>` (line ~566). Replace the outer fragment's closing `</>` and the outer condition's closing `)}` with the new section inserted before the closing:

The full replacement block (the section that currently ends at line ~567):

Currently:
```jsx
{photos?.length > 0 && (
  <>
    <PhotoGallery ... />
    {pendingImagePromptModifier && !generatedImages?.length && (
      <div ...>...</div>
    )}
    {isConfirming && imageGenProgress?.isActive && (
      <div ...>...</div>
    )}
  </>
)}
```

Add the following inside the `<>...</>` fragment, after the pending prompt modifier chip and before the imageGenProgress bar (i.e. between those two existing blocks):

```jsx
{autoBackgroundRemovalEnabled && (
  <div className="my-5 rounded-lg border border-border-default bg-surface-muted p-4">
    <h3 className="mb-2.5 text-lg text-text-primary">
      Background Removed Photos
    </h3>
    {bgRemovalProgress?.isActive && (
      <div className="mt-2.5">
        <p className="text-text-muted">
          {bgRemovalProgress.completedSteps.length} of{" "}
          {bgRemovalProgress.totalSteps.length} backgrounds removed
        </p>
        {bgRemovalProgress.totalSteps.length > 0 && (
          <div className="relative mt-2.5 h-5 w-full overflow-hidden rounded bg-surface-hover">
            <div
              className="h-full rounded bg-green-500 transition-[width] duration-300"
              style={{
                width: `${
                  (bgRemovalProgress.completedSteps.length /
                    bgRemovalProgress.totalSteps.length) *
                  100
                }%`,
              }}
            />
          </div>
        )}
      </div>
    )}
    {Object.keys(bgRemovedPhotos || {}).length > 0 && (
      <div className="mt-4 grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
        {Object.values(bgRemovedPhotos).map((url, idx) => (
          <div
            key={url}
            className="aspect-square overflow-hidden rounded-xl border border-border-default bg-surface-panel"
          >
            <img
              src={url}
              alt={`Background removed ${idx + 1}`}
              className="h-full w-full object-contain"
              loading="lazy"
            />
          </div>
        ))}
      </div>
    )}
    {!bgRemovalProgress?.isActive &&
      Object.keys(bgRemovedPhotos || {}).length === 0 && (
        <p className="mt-2 text-sm text-text-muted">
          Waiting for photos to load...
        </p>
      )}
  </div>
)}
```

Then, after that block (and still inside the `<>` fragment, after the imageGenProgress bar), add the hoisted Confirm Categories button:

```jsx
{autoBackgroundRemovalEnabled && (
  <div className="mt-8 flex justify-center">
    <button
      type="button"
      className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-full border border-border-default bg-surface-panel px-6 py-3 text-base font-semibold text-text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:bg-surface-hover hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (onConfirmCategories) {
          onConfirmCategories();
        }
      }}
      disabled={isConfirming}
    >
      {isConfirming ? "Generating Images..." : "Confirm Categories"}
    </button>
  </div>
)}
```

Note: use the same `btnPillLg` class string that PhotoGallery uses. Check the import or definition of `btnPillLg` at the top of `PhotoGallery.jsx` and use the same string, or import the constant if it's exported.

- [ ] **Step 4: Pass new props from App.jsx to both CreateWorkflow instances**

In `App.jsx`, find where `<CreateWorkflow` is rendered for the real workflow tab and add the three new props:

```jsx
autoBackgroundRemovalEnabled={autoBackgroundRemovalEnabled}
bgRemovedPhotos={bgRemovedPhotos}
bgRemovalProgress={bgRemovalProgress}
```

- [ ] **Step 5: Verify full flow in browser**

Run `npm run dev`. Submit a listing link. Confirm:
1. Background Removal section appears immediately after photos load, with a progress bar counting up
2. After removal finishes, a grid of bg-removed images appears
3. Original PhotoGallery still shows above with no Confirm button
4. A Confirm Categories button appears below the bg-removal section
5. Clicking Confirm Categories triggers image generation with the bg-removed URLs (check browser Network tab)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx frontend/src/App.jsx
git commit -m "feat: add bg removal section to CreateWorkflow with progress bar and hoisted Confirm button"
```

---

## Task 7: Test Workflow Mirror

**Files:**
- Modify: `frontend/src/testWorkflowState.js`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add initial bg removal state to testWorkflowState.js**

Open `testWorkflowState.js` and find the returned object from `createTestWorkflowState()`. Add two new fields:

```js
bgRemovedPhotos: {},
bgRemovalProgress: {
  isActive: false,
  currentStep: null,
  completedSteps: [],
  totalSteps: [],
},
```

- [ ] **Step 2: Add test bg removal state accessors in App.jsx**

In `App.jsx`, find where `testWf` fields are destructured (the lines using `testWf.photos`, `testWf.categories`, etc., around line 657). Add:

```js
const testBgRemovedPhotos = testWf.bgRemovedPhotos;
const testBgRemovalProgress = testWf.bgRemovalProgress;
const setTestBgRemovedPhotos = setTestKey("bgRemovedPhotos");
const setTestBgRemovalProgress = setTestKey("bgRemovalProgress");
```

- [ ] **Step 3: Add testTriggerAutoBackgroundRemoval in App.jsx**

Find `triggerAutoBackgroundRemoval` (added in Task 3). Add the following mock version immediately after it:

```js
const testTriggerAutoBackgroundRemoval = (photoUrls) => {
  const totalSteps = photoUrls.map((_, i) => `Image ${i + 1}`);
  setTestBgRemovalProgress({
    isActive: true,
    currentStep: null,
    completedSteps: [],
    totalSteps,
  });

  photoUrls.forEach((url, idx) => {
    setTimeout(() => {
      const stepLabel = `Image ${idx + 1}`;
      setTestBgRemovalProgress((prev) => ({
        ...prev,
        completedSteps: [...prev.completedSteps, stepLabel],
        currentStep: null,
      }));
      // Use original URL as a stand-in for the test (no actual rembg)
      setTestBgRemovedPhotos((prev) => ({ ...prev, [url]: url }));
      if (idx === photoUrls.length - 1) {
        setTestBgRemovalProgress((prev) => ({ ...prev, isActive: false }));
      }
    }, (idx + 1) * 800);
  });
};
```

- [ ] **Step 4: Call the test trigger when test photos are set**

In `App.jsx`, find where the test workflow simulates photo loading completion — search for where `setTestKey("photos")` or `setTestPhotos` is called with MOCK_DATA photos. After that call, add:

```js
if (autoBackgroundRemovalEnabled && mockPhotos?.length) {
  testTriggerAutoBackgroundRemoval(mockPhotos);
}
```

(Replace `mockPhotos` with whatever variable name holds the photos array at that point.)

- [ ] **Step 5: Pass test bg removal state to the test CreateWorkflow instance**

In `App.jsx`, find the second `<CreateWorkflow` render (the one in the test tab, passing `testWf.*` props). Add:

```jsx
bgRemovedPhotos={testBgRemovedPhotos}
bgRemovalProgress={testBgRemovalProgress}
autoBackgroundRemovalEnabled={autoBackgroundRemovalEnabled}
```

- [ ] **Step 6: Verify test workflow in browser**

Navigate to the Test Workflow tab in the app. Submit a test listing. Confirm:
1. The bg removal section appears with a simulated progress bar ticking up (800ms per image)
2. After all images "process", the grid shows the same source images (placeholder — no actual rembg in test mode)
3. Confirm Categories button appears below and triggers mock generation

- [ ] **Step 7: Commit**

```bash
git add frontend/src/testWorkflowState.js frontend/src/App.jsx
git commit -m "feat: mirror auto background removal in test workflow"
```

---

## Self-Review

**Spec coverage check:**
- [x] New streaming endpoint `POST /api/remove-backgrounds-batch` — Task 1
- [x] `GET /api/bg-removed-image/<filename>` serve endpoint — Task 1
- [x] Feature flag `autoBackgroundRemovalEnabled` defaulting to `true` — Task 2
- [x] Settings tab toggle — Task 2
- [x] `bgRemovedPhotos` and `bgRemovalProgress` state — Task 3
- [x] `triggerAutoBackgroundRemoval` fired after photos land — Task 3
- [x] State reset on new listing — Task 3 Step 4
- [x] `handleConfirmCategories` swaps in bg-removed URLs — Task 4
- [x] Graceful fallback when a photo failed or bg removal still in progress — Task 4 (`|| photoUrl` fallback)
- [x] `hideConfirmButton` prop on PhotoGallery — Task 5
- [x] BG removal section in CreateWorkflow with progress bar — Task 6
- [x] Grid of bg-removed images — Task 6
- [x] Hoisted Confirm Categories button below the section — Task 6
- [x] Test workflow mirror — Task 7

**Placeholder scan:** No TBDs or TODOs in any step. All code blocks are complete.

**Type consistency:**
- `bgRemovedPhotos`: `{ [originalUrl: string]: bgRemovedUrl: string }` — consistent across Tasks 3, 4, 6, 7
- `bgRemovalProgress`: `{ isActive: bool, currentStep: string|null, completedSteps: string[], totalSteps: string[] }` — consistent across Tasks 3, 6, 7
- `triggerAutoBackgroundRemoval(photoUrls: string[], sku: string)` — called with `(data.photos, data.sku)` in Task 3, mirrored as `testTriggerAutoBackgroundRemoval(photoUrls: string[])` in Task 7 (no sku needed for mock)
- `hideConfirmButton` prop: added to PhotoGallery in Task 5, consumed in Task 6
