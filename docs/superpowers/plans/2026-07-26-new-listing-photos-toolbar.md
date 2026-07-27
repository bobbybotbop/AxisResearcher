# New Listing Photos Toolbar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the same Image Editor toolbar buttons (Upload images, Select, Bulk Actions) to the "New Listing Photos" section in CreateWorkflow, plus a Delete action so users can remove individual/bulk generated images before uploading to eBay.

**Architecture:** The New Listing Photos section in `CreateWorkflow.jsx` currently has no toolbar — only a drag-to-reorder grid and per-image hover remove (×) button. We'll add a toolbar row above the grid mirroring the one in `PhotoGallery`, wiring up: (1) Upload Images via the existing `ImageUploadModal` with destination "pool" → adds to `generatedImages` via `onAddToListing`, (2) Select mode with per-image selection UI, (3) Bulk Actions dropdown with Delete. The existing hover remove button (×) stays as a convenience for single deletes while not in select mode.

**Tech Stack:** React state hooks, `@hello-pangea/dnd` (already used), `ImageUploadModal` (already imported), `btnPill` / `btnPillSm` / `btnPillLg` (buttonPill.js)

---

## File Structure

- **Modify only:** `frontend/src/components/CreateWorkflow.jsx`
  - Add local state: `newPhotoSelectMode`, `selectedNewPhotos` (Set of indices), `newPhotoBulkDropdownOpen`, `showNewPhotoUploadModal`
  - Add toolbar JSX above the DragDropContext
  - Add selection overlay on each Draggable image tile
  - Add upload modal instance
  - Wire delete (single via toolbar select + bulk action; the existing hover × already calls `onRemoveFromListing`)

No new files, no changes to `App.jsx`, `PhotoGallery.jsx`, or `ImageUploadModal.jsx`. All required callbacks (`onAddToListing`, `onRemoveFromListing`) are already passed as props.

---

### Task 1: Add local state for new-listing-photos toolbar

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:90-93` (existing useState block)

- [ ] **Step 1: Add four new state variables** after the existing `useState` declarations at the top of the `CreateWorkflow` function body (around line 90):

```jsx
const [newPhotoSelectMode, setNewPhotoSelectMode] = useState(false);
const [selectedNewPhotos, setSelectedNewPhotos] = useState(new Set());
const [newPhotoBulkDropdownOpen, setNewPhotoBulkDropdownOpen] = useState(false);
const [showNewPhotoUploadModal, setShowNewPhotoUploadModal] = useState(false);
```

- [ ] **Step 2: Add click-outside listener to close the new bulk dropdown**, right after the existing `useEffect` for `isEditorOpen` (around line 103):

```jsx
useEffect(() => {
  if (!newPhotoBulkDropdownOpen) return;
  const close = () => setNewPhotoBulkDropdownOpen(false);
  document.addEventListener("click", close);
  return () => document.removeEventListener("click", close);
}, [newPhotoBulkDropdownOpen]);
```

- [ ] **Step 3: Verify no errors** — run `npm run dev:frontend` (from project root) and confirm the dev server starts without compile errors. Then stop it.

---

### Task 2: Add toolbar row above the DragDropContext in the "New Listing Photos" section

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx` — the `generatedImages?.length > 0` block, specifically the `<h2>New Listing Photos</h2>` line (around line 659-663)

The current code reads:
```jsx
{generatedImages?.length > 0 && (
  <div className="mt-8 rounded-2xl border border-border-default bg-surface-panel p-6">
    <h2 className="mb-5 text-xl font-semibold text-text-primary">
      New Listing Photos
    </h2>
    <DragDropContext onDragEnd={onDragEnd}>
```

- [ ] **Step 1: Replace the `<h2>` with a header row containing the toolbar** — replace this chunk in the file:

Old:
```jsx
    <h2 className="mb-5 text-xl font-semibold text-text-primary">
      New Listing Photos
    </h2>
    <DragDropContext onDragEnd={onDragEnd}>
```

New:
```jsx
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-xl font-semibold text-text-primary">New Listing Photos</h2>
      <div className="flex flex-wrap items-center gap-2">
        {onOpenEditor && (
          <button type="button" className={btnPill} onClick={onOpenEditor}>
            Image Editor
          </button>
        )}
        <button
          type="button"
          className={btnPill}
          onClick={() => setShowNewPhotoUploadModal(true)}
        >
          Upload Images
        </button>
        <button
          type="button"
          className={`${btnPill} ${newPhotoSelectMode ? "ring-2 ring-inset ring-blue-500" : ""}`}
          onClick={() => {
            setNewPhotoSelectMode((prev) => {
              if (prev) {
                setSelectedNewPhotos(new Set());
                setNewPhotoBulkDropdownOpen(false);
              }
              return !prev;
            });
          }}
        >
          {newPhotoSelectMode ? "Done" : "Select"}
        </button>
        <div className="relative">
          <button
            type="button"
            className={btnPill}
            disabled={!newPhotoSelectMode || selectedNewPhotos.size === 0}
            onClick={(e) => {
              e.stopPropagation();
              setNewPhotoBulkDropdownOpen((prev) => !prev);
            }}
          >
            Bulk Actions ▾
          </button>
          {newPhotoBulkDropdownOpen && (
            <div className="absolute right-0 top-full z-20 mt-1 min-w-30 rounded-lg border border-border-default bg-surface-panel py-1 shadow-lg">
              <button
                type="button"
                className="w-full px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-app"
                onClick={() => {
                  const indices = Array.from(selectedNewPhotos).sort((a, b) => b - a);
                  indices.forEach((idx) => onRemoveFromListing(idx));
                  setSelectedNewPhotos(new Set());
                  setNewPhotoSelectMode(false);
                  setNewPhotoBulkDropdownOpen(false);
                }}
              >
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
    <DragDropContext onDragEnd={onDragEnd}>
```

Note: `btnPill` is already imported at line 9 from `"../styles/buttonPill"`. `onOpenEditor` is already a prop (it's passed as `onEditorToggle` from App.jsx — check the prop name used in CreateWorkflow). Looking at lines 40 and 867: the prop received is `onEditorToggle`, so use `onEditorToggle` not `onOpenEditor`:

Replace `{onOpenEditor && (` with `{onEditorToggle && (` and `onClick={onOpenEditor}` with `onClick={onEditorToggle}` in the snippet above.

- [ ] **Step 2: Check the dev server compiles** — run `npm run dev:frontend` and verify no errors, then stop.

---

### Task 3: Add selection overlay to each generated image tile

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx` — inside the `Draggable` render, the image `<div>` (around line 687-734)

The outer draggable div currently has `imageSelectionActive` toggling its classNames. We need `newPhotoSelectMode` to also drive selection highlighting (separate from the photo-regeneration `imageSelectionActive` mode).

- [ ] **Step 1: Add toggle handler for new-photo selection** — when a tile is clicked while `newPhotoSelectMode` is true, toggle the index in `selectedNewPhotos`. Currently, clicks in `imageSelectionActive` mode call `onImageSelection(index)`. We need to add a new branch.

Find this block inside the `<div className="group relative aspect-square ...">` onClick:
```jsx
onClick={() => {
  if (imageSelectionActive && onImageSelection) {
    onImageSelection(index);
  }
}}
```

Replace with:
```jsx
onClick={() => {
  if (newPhotoSelectMode) {
    setSelectedNewPhotos((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  } else if (imageSelectionActive && onImageSelection) {
    onImageSelection(index);
  }
}}
```

- [ ] **Step 2: Add selection ring and checkmark overlay** to the same image tile. After the existing `imageSelectionActive && isSelected` checkmark block (around line 716-720), add a `newPhotoSelectMode` ring overlay. Find:

```jsx
{imageSelectionActive && isSelected && (
  <div className="pointer-events-none absolute left-1.5 top-1.5 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white shadow">
    &#10003;
  </div>
)}
```

After that block, add:
```jsx
{newPhotoSelectMode && selectedNewPhotos.has(index) && (
  <div className="pointer-events-none absolute inset-0 z-10 rounded-xl ring-4 ring-inset ring-blue-500">
    <div className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-white">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
      </svg>
    </div>
  </div>
)}
```

- [ ] **Step 3: Dim unselected tiles in select mode** — add `newPhotoSelectMode` dim class to the outer div className. Find the current className string that includes `imageSelectionActive ? "animate-jiggle" : ""`. It currently looks like:

```jsx
className={`group relative aspect-square cursor-grab overflow-hidden rounded-xl transition-all active:cursor-grabbing ${
  snapshot.isDragging ? "opacity-80 shadow-lg" : ""
} ${imageSelectionActive ? "animate-jiggle" : ""} ${
  imageSelectionActive && isSelected
    ? "ring-3 ring-blue-500 ring-offset-2"
    : ""
} ${
  imageSelectionActive && !isSelected
    ? "opacity-40"
    : ""
}`}
```

Replace with:
```jsx
className={`group relative aspect-square cursor-grab overflow-hidden rounded-xl transition-all active:cursor-grabbing ${
  snapshot.isDragging ? "opacity-80 shadow-lg" : ""
} ${imageSelectionActive ? "animate-jiggle" : ""} ${
  imageSelectionActive && isSelected
    ? "ring-3 ring-blue-500 ring-offset-2"
    : ""
} ${
  imageSelectionActive && !isSelected
    ? "opacity-40"
    : ""
} ${
  newPhotoSelectMode && !selectedNewPhotos.has(index)
    ? "opacity-60"
    : ""
}`}
```

- [ ] **Step 4: Compile check** — `npm run dev:frontend`, no errors, stop.

---

### Task 4: Add ImageUploadModal instance for new listing photos

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx` — after the closing `</div>` of the `generatedImages?.length > 0` section (just before the `{lightboxOpen ...}` block)

`ImageUploadModal` is already imported at line 3. We need an instance that sends images to `onAddToListing` (not `onAddToOriginalPhotos`).

- [ ] **Step 1: Add the modal** — find the end of the `generatedImages?.length > 0` block, just before:
```jsx
      {lightboxOpen && photos?.length > 0 && (
```

Before that line, add:
```jsx
      <ImageUploadModal
        isOpen={showNewPhotoUploadModal}
        onClose={() => setShowNewPhotoUploadModal(false)}
        onAddImages={(images, destination) => {
          if (destination === "pool" || destination === "original") {
            const urls = Array.isArray(images)
              ? images.map((img) => (typeof img === "string" ? img : img.dataUrl))
              : [];
            urls.forEach((url) => onAddToListing(url));
          }
        }}
        canAddToOriginal={false}
        mode="pool"
      />
```

Note: `ImageUploadModal` in pool mode passes `pendingImages` objects (with `.dataUrl`) when destination is "pool", and plain URL strings when destination is "original". The handler above normalises both shapes to strings before calling `onAddToListing`.

- [ ] **Step 2: Full smoke test** — run `npm run dev` (starts both backend and frontend). Open the app, fetch a listing, generate images. Then:
  - Confirm the toolbar appears above New Listing Photos with "Upload Images", "Select", "Bulk Actions ▾", "Image Editor" buttons
  - Click "Upload Images" → modal opens → add a local image file → it appears in the grid
  - Click "Select" → button gets blue ring, all images slightly dimmed
  - Click tiles → blue ring + checkmark appear
  - Click "Bulk Actions ▾" (enabled when ≥1 selected) → "Delete" option → selected images removed
  - Click "Done" → select mode exits, selection cleared
  - Confirm existing hover × remove still works when not in select mode
  - Confirm drag-to-reorder still works when not in select mode

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: add image editor toolbar to New Listing Photos section"
```

---

## Self-Review Notes

- Bulk delete uses descending index sort before iterating so index shifts don't corrupt removal — `indices.sort((a, b) => b - a)` before calling `onRemoveFromListing` for each. This is correct because `onRemoveFromListing` in App.jsx filters the array in place and re-syncs to disk each call.
- `showNewPhotoUploadModal` state is inside `CreateWorkflow`, not `App.jsx` — consistent with how `PhotoGallery` manages its own `showUploadModal` state locally.
- The `mode="pool"` prop on the new modal hides the destination radio buttons and sends images as `{dataUrl, name}` objects to `onAddImages`. The handler normalizes to plain URL strings before calling `onAddToListing`.
- No changes needed to `App.jsx`, `PhotoGallery.jsx`, or any backend files.
