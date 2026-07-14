# Original Photos Select Mode & Bulk Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Select mode toggle and a Bulk Actions (Skip) dropdown to the Original Photos header row, with per-image selection highlights, all self-contained in `PhotoGallery.jsx`.

**Architecture:** All new state (`selectMode`, `selectedPhotos`, `bulkDropdownOpen`) lives locally in `PhotoGallery.jsx`. The Select button toggles select mode; in select mode image clicks toggle selection instead of opening the lightbox. Bulk Actions → Skip calls the existing `onSkipPhoto` prop for each selected image then exits select mode.

**Tech Stack:** React (useState, useCallback), Tailwind v4, existing `btnPill` style token from `../styles/buttonPill`

---

### Task 1: Add select mode state and wire the Select button

**Files:**
- Modify: `frontend/src/components/PhotoGallery.jsx`

- [ ] **Step 1: Add three new state variables** inside the component, right after the existing `showUploadModal` state on line 18:

```jsx
const [showUploadModal, setShowUploadModal] = useState(false);
const [selectMode, setSelectMode] = useState(false);
const [selectedPhotos, setSelectedPhotos] = useState(new Set());
const [bulkDropdownOpen, setBulkDropdownOpen] = useState(false);
```

- [ ] **Step 2: Add a toggle handler** for the Select button. Add this after the `handleSkipClick` function (around line 73, before the `return`):

```jsx
const toggleSelectMode = () => {
  setSelectMode((prev) => {
    if (prev) {
      setSelectedPhotos(new Set());
      setBulkDropdownOpen(false);
    }
    return !prev;
  });
};

const togglePhotoSelection = (index) => {
  setSelectedPhotos((prev) => {
    const next = new Set(prev);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    return next;
  });
};
```

- [ ] **Step 3: Add the Select button to the header row.** Replace the header button group (lines 79–94) with:

```jsx
<div className="flex flex-wrap items-center gap-2">
  {onOpenEditor && (
    <button type="button" className={btnPill} onClick={onOpenEditor}>
      Image Editor
    </button>
  )}
  {onAddToOriginalPhotos && (
    <button
      type="button"
      className={btnPill}
      onClick={() => setShowUploadModal(true)}
    >
      Upload Images
    </button>
  )}
  <button
    type="button"
    className={`${btnPill} ${selectMode ? "ring-2 ring-inset ring-blue-500" : ""}`}
    onClick={toggleSelectMode}
  >
    {selectMode ? "Done" : "Select"}
  </button>
  <div className="relative">
    <button
      type="button"
      className={btnPill}
      disabled={!selectMode || selectedPhotos.size === 0}
      onClick={() => setBulkDropdownOpen((prev) => !prev)}
    >
      Bulk Actions ▾
    </button>
    {bulkDropdownOpen && (
      <div className="absolute right-0 top-full z-20 mt-1 min-w-[120px] rounded-lg border border-border-default bg-surface-panel py-1 shadow-lg">
        <button
          type="button"
          className="w-full px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-app"
          onClick={() => {
            selectedPhotos.forEach((idx) => {
              const photoUrl = photos[idx];
              if (onSkipPhoto) onSkipPhoto(photoUrl);
            });
            setSelectedPhotos(new Set());
            setSelectMode(false);
            setBulkDropdownOpen(false);
          }}
        >
          Skip
        </button>
      </div>
    )}
  </div>
</div>
```

- [ ] **Step 4: Wire image onClick to respect select mode.** Replace the `onClick` on the image tile `div` (line 106):

```jsx
onClick={() => {
  if (selectMode) {
    togglePhotoSelection(index);
  } else {
    onPhotoClick && onPhotoClick(index);
  }
}}
```

- [ ] **Step 5: Hide the per-image skip button in select mode.** Change the condition wrapping the skip button (line 108) from:

```jsx
{onSkipPhoto && (
```

to:

```jsx
{onSkipPhoto && !selectMode && (
```

- [ ] **Step 6: Add selection highlight overlay.** Add this block inside the image tile `div`, after the existing `isSkipped` label block (after line 139), before the `showClassification` block:

```jsx
{selectMode && selectedPhotos.has(index) && (
  <div className="pointer-events-none absolute inset-0 z-10 rounded-xl ring-4 ring-inset ring-blue-500">
    <div className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-white">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
      </svg>
    </div>
  </div>
)}
```

- [ ] **Step 7: Close the bulk dropdown when clicking outside.** Add `useEffect` to the existing import on line 1:

```jsx
import { useState, useCallback, useEffect } from "react";
```

Then add this effect after the state declarations:

```jsx
useEffect(() => {
  if (!bulkDropdownOpen) return;
  const close = () => setBulkDropdownOpen(false);
  document.addEventListener("click", close);
  return () => document.removeEventListener("click", close);
}, [bulkDropdownOpen]);
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/PhotoGallery.jsx
git commit -m "feat: add Select mode and Bulk Actions (Skip) to Original Photos"
```

---

## Verification

- [ ] Run `npm run dev` (from project root) and open the Create tab
- [ ] Confirm header shows: `Image Editor` | `Upload Images` | `Select` | `Bulk Actions ▾` (grayed out)
- [ ] Click **Select** → button shows active ring + "Done" label; Bulk Actions still disabled (nothing selected)
- [ ] Click images → each gets blue ring + checkmark; Bulk Actions becomes enabled
- [ ] Open **Bulk Actions → Skip** → selected images show SKIPPED, mode exits, selection clears
- [ ] Click **Done** without any action → mode exits, images unaffected
- [ ] Outside select mode: clicking an image opens the Lightbox as before
- [ ] Confirm category `<select>` dropdowns still work normally
- [ ] Confirm per-image skip button (top-right ×) is hidden while in select mode and visible outside it
- [ ] Click outside the Bulk Actions dropdown → it closes
