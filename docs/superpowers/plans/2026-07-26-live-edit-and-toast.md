# Live Edit Auto-Save + Toast Notification System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual Save Title/Description buttons with 800ms debounced auto-save, and replace all inline error rendering (and native `alert()` calls) with a fixed-position toast notification system.

**Architecture:** A new `ToastContainer.jsx` renders via React portal at a fixed top-center position, fed by `toasts` state + `addToast`/`removeToast` helpers in `App.jsx`. The global `error` state is removed entirely; all `setError(...)` calls become `addToast('error', ...)`. Two `useEffect` hooks in `App.jsx` watch `editableTitle` and `editableDescription`, debouncing saves to the existing `/api/update-title` and `/api/update-description` endpoints. `CreateWorkflow.jsx` loses the Save buttons and gains inline "Saving..." / "Saved" status hints.

**Tech Stack:** React, ReactDOM.createPortal, Tailwind v4 CSS tokens

---

### Task 1: Create ToastContainer.jsx

**Files:**
- Create: `frontend/src/components/ToastContainer.jsx`

- [ ] **Step 1: Create the file**

```jsx
import { useEffect } from "react";
import ReactDOM from "react-dom";

function Toast({ toast, onRemove }) {
  useEffect(() => {
    if (toast.type === "success") {
      const t = setTimeout(() => onRemove(toast.id), 4000);
      return () => clearTimeout(t);
    }
  }, [toast.id, toast.type, onRemove]);

  const isSuccess = toast.type === "success";
  return (
    <div
      className={`flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg ${
        isSuccess ? "bg-success text-white" : "bg-red-600 text-white"
      }`}
      style={{ minWidth: "280px", maxWidth: "480px" }}
    >
      <span className="mt-0.5 shrink-0 text-sm font-bold">
        {isSuccess ? "✓" : "✕"}
      </span>
      <div className="flex-1">
        <p className="text-sm font-medium leading-snug">{toast.message}</p>
        {toast.detail && (
          <p className="mt-0.5 text-xs opacity-80">{toast.detail}</p>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="ml-1 shrink-0 text-sm opacity-60 hover:opacity-100"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export default function ToastContainer({ toasts, onRemove }) {
  if (toasts.length === 0) return null;
  return ReactDOM.createPortal(
    <div
      className="flex flex-col gap-2"
      style={{
        position: "fixed",
        top: "1rem",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
      }}
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body,
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ToastContainer.jsx
git commit -m "feat: add ToastContainer portal component"
```

---

### Task 2: Wire toast state into App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add ToastContainer import near the top of App.jsx with the other component imports**

Find the block of component imports (near `import CreateWorkflow`) and add:
```js
import ToastContainer from "./components/ToastContainer";
```

- [ ] **Step 2: Add toast state and helpers in App.jsx, directly after the `uploadResult` state declaration (line 236)**

```js
const [toasts, setToasts] = useState([]);
const addToast = (type, message, detail) => {
  const id = Date.now() + Math.random();
  setToasts((prev) => [...prev, { id, type, message, detail }]);
};
const removeToast = (id) => {
  setToasts((prev) => prev.filter((t) => t.id !== id));
};
```

- [ ] **Step 3: Render ToastContainer in the App return JSX**

Find the outermost wrapper div in the App return (the one containing `<main>`, sidebar, etc.) and add `<ToastContainer>` as the first child, before the sidebar/main divs:

```jsx
<ToastContainer toasts={toasts} onRemove={removeToast} />
```

- [ ] **Step 4: Start the dev server and verify no errors in the console**

```
npm run dev
```

Expected: app loads normally, no console errors. No toasts visible yet.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire toast state and ToastContainer into App"
```

---

### Task 3: Migrate all inline errors to toasts; remove error state

This task touches `App.jsx` (all `setError` calls) and `CreateWorkflow.jsx` (inline error renders + error prop). Do all changes before committing.

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/CreateWorkflow.jsx`

- [ ] **Step 1: Remove `error` state declaration from App.jsx**

Delete line 225:
```js
const [error, setError] = useState(null);
```

- [ ] **Step 2: Replace every `setError(message)` call in App.jsx with `addToast('error', message)`**

Replace each of the following. Every `setError(null)` line is simply deleted (it was resetting the error banner, which no longer exists).

**`fetchListingPhotos`:**
```js
// delete: setError(null);
// replace: setError("Please enter an eBay listing ID or URL")
addToast("error", "Please enter an eBay listing ID or URL");
// replace: setError(err.message || "An error occurred while fetching the listing")
addToast("error", err.message || "An error occurred while fetching the listing");
```

**`regenerateTitle`:**
```js
// delete: setError(null) if present
// replace: setError(data.error || "Failed to regenerate title")
addToast("error", data.error || "Failed to regenerate title");
// replace: setError(err.message || "Failed to regenerate title")
addToast("error", err.message || "Failed to regenerate title");
```

**`regenerateDescription`:**
```js
addToast("error", data.error || "Failed to regenerate description");
addToast("error", err.message || "Failed to regenerate description");
```

**`regenerateMetadata`:**
```js
addToast("error", data.error || "Failed to regenerate metadata");
addToast("error", err.message || "Failed to regenerate metadata");
```

**Image generation polling (inside `handleConfirmCategories`):**
```js
addToast("error", errorMsg); // was: setError(errorMsg) — partial/failed generation
addToast("error", "Error checking generation status");
addToast("error", err.message || "An error occurred while generating images");
```

**`handleRegenerateImages`:**
```js
addToast("error", "Please enter a prompt to guide the regeneration");
// delete: setError(null)
addToast("error", err.message || "An error occurred while regenerating images");
```

**`handleTrimSelected`:**
```js
// delete: setError(null)
addToast("error", err.message || "An error occurred while trimming images");
```

**`handleAddNewVersions`:**
```js
addToast("error", "Please enter a prompt to guide the new version");
addToast("error", "SKU is required. Please fetch photos first.");
addToast("error", "No valid images to regenerate");
// delete: setError(null)
addToast("error", err.message || "An error occurred while adding new version");
```

**`handleCreateListing`:**
```js
addToast("error", "Original listing data is required");
addToast("error", "SKU is required. Please fetch photos first.");
// delete: setError(null)
addToast("error", err.message || "An error occurred while creating listing");
```

**`handleTrimTitle`:**
```js
// delete: setError(null)
addToast("error", err.message || "Failed to trim title");
```

**`handleSaveTitle`:**
```js
// delete: setIsSavingTitle(true); setError(null);
// replace: setError(err.message || "Failed to save title")
addToast("error", err.message || "Failed to save title");
// delete: setIsSavingTitle(false) in finally
```
(The full rewrite of handleSaveTitle happens in Task 6.)

**`handleSaveDescription`:**
```js
// delete: setIsSavingDescription(true); setError(null);
// replace: setError(err.message || "Failed to save description")
addToast("error", err.message || "Failed to save description");
// delete: setIsSavingDescription(false) in finally
```
(Full rewrite happens in Task 6.)

**`fetchAllListings`:**
```js
// delete: setError(null)
addToast("error", err.message || "An error occurred while fetching listings");
```

**`performRestock`:**
```js
addToast("error", `Failed to restock ${data.failed.length} listing(s)`);
addToast("error", err.message || "Failed to restock listings");
```

**`handleUploadToEbay`:**
```js
addToast("error", "No SKU provided");
// delete: setError(null)
addToast("error", err.message || "An error occurred while uploading listing");
```

**`handleTestingFunction`:**
```js
// delete: setError(null)
addToast("error", err.message || "An error occurred while running testing function");
```

**`handleListingClick`:**
```js
// delete: setError(null)
addToast("error", err.message || "An error occurred while fetching listing details");
```

- [ ] **Step 3: Update `onListingIdChange` handler in the CreateWorkflow JSX props (around line 3714)**

Old:
```js
onListingIdChange={(v) => { setListingId(v); if (!listingLinkSubmitted) setError(null); }}
```
New:
```js
onListingIdChange={setListingId}
```

- [ ] **Step 4: Remove `error={error}` from the CreateWorkflow JSX props**

Delete:
```jsx
error={error}
```

- [ ] **Step 5: In CreateWorkflow.jsx, remove the `error` prop from the destructuring**

Delete `error = null,` from the destructured prop list (line 32).

- [ ] **Step 6: In CreateWorkflow.jsx, remove the two inline error render blocks**

Delete lines 191–193 (the pre-submission small red text):
```jsx
{!listingLinkSubmitted && error && (
  <p className="mt-3 text-center text-sm text-red-500">{error}</p>
)}
```

Delete lines 196–200 (the post-submission red box):
```jsx
{listingLinkSubmitted && error && (
  <div className="mb-8 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
    <p>{error}</p>
  </div>
)}
```

- [ ] **Step 7: In CreateWorkflow.jsx, remove `hasError` from the MessageBarInput call**

Find `hasError={!listingLinkSubmitted && Boolean(error)}` (line 188) and delete that prop line entirely.

- [ ] **Step 8: Verify no remaining references to `error` (as a prop/state) exist**

Search the two files:
```
grep -n "setError\|error={error}\|Boolean(error)\| error &&" frontend/src/App.jsx frontend/src/components/CreateWorkflow.jsx
```
Expected: zero matches (only comments or unrelated variable names like `errorMsg` are OK).

- [ ] **Step 9: Start the dev server and test**

```
npm run dev
```

Submit an invalid eBay URL. A red toast should appear at the top of the screen. No inline red box should appear anywhere in the page.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: replace inline error state with toast notifications"
```

---

### Task 4: Replace alert() calls in ImageCanvas.jsx with toast

**Files:**
- Modify: `frontend/src/components/ImageCanvas.jsx`
- Modify: `frontend/src/components/CreateWorkflow.jsx`
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add `onError` prop to ImageCanvas**

Find the ImageCanvas component function signature and add `onError` to its prop destructuring. It likely looks like:
```js
function ImageCanvas({ ..., useRealUpload, onRequestClose, onAddToListing, ... })
```
Add `, onError = () => {}` to the destructured props.

- [ ] **Step 2: Replace the two `alert()` calls in ImageCanvas.jsx with `onError`**

Line 401 — early-return guard:
```js
// Old:
alert("No images on the canvas to add.");
// New:
onError("No images on the canvas to add.");
```

Line 451 — catch block:
```js
// Old:
alert("Failed to add image to listing: " + err.message);
// New:
onError("Failed to add image to listing: " + err.message);
```

- [ ] **Step 3: Add `onError` prop to CreateWorkflow.jsx**

In the CreateWorkflow prop destructuring, add:
```js
onError = () => {},
```

Find where `<ImageCanvas>` is rendered in CreateWorkflow.jsx and pass the prop through:
```jsx
<ImageCanvas
  ...existing props...
  onError={onError}
/>
```

- [ ] **Step 4: Pass `onError` from App.jsx to CreateWorkflow**

In the `<CreateWorkflow>` JSX call in App.jsx, add:
```jsx
onError={(msg) => addToast("error", msg)}
```

- [ ] **Step 5: Test**

Open the ImageCanvas editor while no images are on the canvas and click "Add to Listing". A red toast should appear instead of a native browser `alert()` dialog.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ImageCanvas.jsx frontend/src/components/CreateWorkflow.jsx frontend/src/App.jsx
git commit -m "feat: replace ImageCanvas alert() with toast notifications"
```

---

### Task 5: Add upload success toasts

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add a success toast in `handleUploadToEbay` after the upload results are stored**

Find this block in `handleUploadToEbay` (around line 2229–2238):
```js
// Store result for this specific SKU
setUploadResults((prev) => ({
  ...prev,
  [sku]: data.upload_result,
}));

// If uploading from the create tab, also update the main upload result
if (sku === listingData?.sku) {
  setUploadResult(data.upload_result);
}
```

Add directly after (before `fetchAllListings()`):
```js
addToast(
  "success",
  "Upload successful",
  data.upload_result.listingId
    ? `Listing ID: ${data.upload_result.listingId}`
    : "Listing is now live on eBay",
);
```

- [ ] **Step 2: Test**

Upload a listing from the History tab while scrolled down. A green success toast should appear at the top of the screen. The inline success strip in the CompactListingRow should also appear as before.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add success toast on eBay upload"
```

---

### Task 6: Add debounced auto-save for title and description in App.jsx

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Remove `isSavingTitle` and `isSavingDescription` state declarations**

Delete lines 379 and 381:
```js
const [isSavingTitle, setIsSavingTitle] = useState(false);
const [isSavingDescription, setIsSavingDescription] = useState(false);
```

- [ ] **Step 2: Add `autoSaveStatus` state and persisted-value refs, directly after the `editableDescription` state declaration (line 380 after previous deletion)**

```js
const [autoSaveStatus, setAutoSaveStatus] = useState({
  title: "idle",
  description: "idle",
});
const persistedTitleRef = useRef("");
const persistedDescriptionRef = useRef("");
```

- [ ] **Step 3: Add a useEffect that syncs the persisted refs when listingData loads**

Place this after the existing `useEffect` hooks that depend on `listingData`, or group with the other listingData effects:

```js
useEffect(() => {
  const title = listingData?.inventoryItem?.product?.title ?? "";
  const description = listingData?.inventoryItem?.product?.description ?? "";
  persistedTitleRef.current = title;
  persistedDescriptionRef.current = description;
}, [listingData]);
```

- [ ] **Step 4: Rewrite `handleSaveTitle` to accept the value as a parameter and use `autoSaveStatus`**

Replace the existing `handleSaveTitle` function (currently lines 1949–1973, adjusted for prior deletions) with:

```js
const handleSaveTitle = async (titleToSave) => {
  const sku = currentSku;
  if (!titleToSave || !sku) return;
  setAutoSaveStatus((prev) => ({ ...prev, title: "saving" }));
  try {
    const response = await fetch("/api/update-title", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sku, title: titleToSave }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Failed to update title");
    if (data.listing_data) {
      setListingData(data.listing_data);
      const saved =
        data.listing_data?.inventoryItem?.product?.title || titleToSave;
      persistedTitleRef.current = saved;
    }
    setAutoSaveStatus((prev) => ({ ...prev, title: "saved" }));
    setTimeout(
      () =>
        setAutoSaveStatus((prev) =>
          prev.title === "saved" ? { ...prev, title: "idle" } : prev,
        ),
      2000,
    );
  } catch (err) {
    console.error("Error saving title:", err);
    addToast("error", err.message || "Failed to save title");
    setAutoSaveStatus((prev) => ({ ...prev, title: "idle" }));
  }
};
```

- [ ] **Step 5: Rewrite `handleSaveDescription` similarly**

Replace the existing `handleSaveDescription` function with:

```js
const handleSaveDescription = async (descToSave) => {
  const sku = currentSku || listingData?.sku;
  if (!sku || !listingData) return;
  setAutoSaveStatus((prev) => ({ ...prev, description: "saving" }));
  try {
    const response = await fetch("/api/update-description", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sku, description: descToSave }),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.error || "Failed to update description");
    if (data.listing_data) {
      setListingData(data.listing_data);
      const saved =
        data.listing_data?.inventoryItem?.product?.description ?? descToSave;
      persistedDescriptionRef.current = saved;
    }
    setAutoSaveStatus((prev) => ({ ...prev, description: "saved" }));
    setTimeout(
      () =>
        setAutoSaveStatus((prev) =>
          prev.description === "saved"
            ? { ...prev, description: "idle" }
            : prev,
        ),
      2000,
    );
  } catch (err) {
    console.error("Error saving description:", err);
    addToast("error", err.message || "Failed to save description");
    setAutoSaveStatus((prev) => ({ ...prev, description: "idle" }));
  }
};
```

- [ ] **Step 6: Add the two debounced-save useEffect hooks**

Place these after the listingData sync effect from Step 3:

```js
useEffect(() => {
  if (!currentSku) return;
  if (!editableTitle) return;
  if (editableTitle === persistedTitleRef.current) return;
  const timer = setTimeout(() => {
    handleSaveTitle(editableTitle);
  }, 800);
  return () => clearTimeout(timer);
}, [editableTitle, currentSku]); // eslint-disable-line react-hooks/exhaustive-deps

useEffect(() => {
  const sku = currentSku || listingData?.sku;
  if (!sku || !listingData) return;
  if (!editableDescription && editableDescription !== "") return;
  if (editableDescription === persistedDescriptionRef.current) return;
  const timer = setTimeout(() => {
    handleSaveDescription(editableDescription);
  }, 800);
  return () => clearTimeout(timer);
}, [editableDescription, currentSku, listingData?.sku]); // eslint-disable-line react-hooks/exhaustive-deps
```

- [ ] **Step 7: Remove `isSavingTitle`, `isSavingDescription`, `onSaveTitle`, `onSaveDescription` from the CreateWorkflow JSX props, and add `autoSaveStatus`**

In the `<CreateWorkflow>` JSX call, make these changes:

Delete:
```jsx
isSavingTitle={isSavingTitle}
isSavingDescription={isSavingDescription}
onSaveTitle={handleSaveTitle}
onSaveDescription={handleSaveDescription}
```

Add:
```jsx
autoSaveStatus={autoSaveStatus}
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: debounced auto-save for title and description"
```

---

### Task 7: Update CreateWorkflow.jsx — remove save buttons, add status hints

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx`

- [ ] **Step 1: Update prop destructuring — remove old save props, add `autoSaveStatus`**

In the CreateWorkflow function signature, make these changes:

Remove:
```js
isSavingTitle,
isSavingDescription,
onSaveTitle,
onSaveDescription,
```

Add:
```js
autoSaveStatus = { title: "idle", description: "idle" },
```

- [ ] **Step 2: Remove the "Save Title" conditional button block**

Delete lines 315–325 (the block that reads):
```jsx
{listingData &&
  editableTitle !==
    (listingData.inventoryItem?.product?.title || "") && (
  <button
    type="button"
    className={btnPillSm}
    onClick={onSaveTitle}
    disabled={isSavingTitle}
  >
    {isSavingTitle ? "Saving..." : "Save Title"}
  </button>
)}
```

- [ ] **Step 3: Add the title auto-save status hint**

Find the flex row that contains the title label and character count badge. It looks like:
```jsx
<div className="flex flex-wrap items-center justify-between gap-2">
```
Inside that row, find the `<strong>` or label for the title. Add the status hint span right after the label text:

```jsx
<div className="flex items-center gap-2">
  <strong className="text-primary">Title:</strong>
  {autoSaveStatus.title === "saving" && (
    <span className="text-xs text-text-muted">Saving...</span>
  )}
  {autoSaveStatus.title === "saved" && (
    <span className="text-xs text-emerald-600">Saved</span>
  )}
</div>
```

If the label is already wrapped in a div, integrate the hint spans into that wrapper instead of adding a new div.

- [ ] **Step 4: Remove the "Save Description" conditional button block**

Delete lines 367–379 (the block that reads):
```jsx
{!isGeneratingText &&
  listingData &&
  editableDescription !==
    (listingData.inventoryItem?.product?.description || "") && (
  <button
    type="button"
    className={`mt-2 ${btnPillSm}`}
    onClick={onSaveDescription}
    disabled={isSavingDescription}
  >
    {isSavingDescription ? "Saving..." : "Save Description"}
  </button>
)}
```

- [ ] **Step 5: Add the description auto-save status hint**

Find the flex row with the description label (line 331–333):
```jsx
<div className="flex flex-wrap items-center justify-between gap-2">
  <strong className="text-primary">Description:</strong>
```

Change to:
```jsx
<div className="flex flex-wrap items-center justify-between gap-2">
  <div className="flex items-center gap-2">
    <strong className="text-primary">Description:</strong>
    {autoSaveStatus.description === "saving" && (
      <span className="text-xs text-text-muted">Saving...</span>
    )}
    {autoSaveStatus.description === "saved" && (
      <span className="text-xs text-emerald-600">Saved</span>
    )}
  </div>
```

- [ ] **Step 6: Start the dev server and run the full verification**

```
npm run dev
```

Verify all of the following:

1. **Auto-save title:** Open a listing, edit the title. After ~800ms of no typing, "Saving..." appears next to "Title:", then "Saved" for 2s, then clears. No save button visible.
2. **Auto-save description:** Click "Edit HTML", edit the description. Same "Saving..." / "Saved" cycle appears next to "Description:".
3. **Toast errors:** Submit an invalid listing URL. Red toast appears fixed at the top. No inline red box.
4. **Toast persists:** Trigger an error. Toast stays until you click X. Success toasts disappear automatically after 4s.
5. **Upload success toast:** Upload a listing from the History tab. Green success toast at top of screen regardless of scroll position.
6. **No save buttons:** Confirm "Save Title" and "Save Description" buttons are gone.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: remove save buttons, add auto-save status hints in CreateWorkflow"
```
