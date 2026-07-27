# Live Title/Description Auto-Save + Toast Notification System

**Date:** 2026-07-26

## Context

Two UX gaps exist in the listing workflow:

1. **Edits to title/description require a manual "Save" click before Upload reads them.** If a user edits the title and immediately clicks "Upload to eBay", the upload uses the stale on-disk version because the save hadn't been triggered yet. The explicit Save buttons create unnecessary friction and a subtle data-loss footgun.

2. **Success and error notifications are buried in the scroll flow.** The "Upload Successful" card and all `error` state renders sit inline in the page — if the user is scrolled down, they miss them entirely. Upload errors on the History tab are completely invisible (the error renders inside CreateWorkflow, not on the upload tab at all). Native `alert()` calls in `ImageCanvas.jsx` are additionally jarring.

---

## Part 1: Debounced Auto-Save for Title and Description

### Behavior

- When the user stops typing in the title or description field for **800ms**, auto-save fires automatically via the existing `/api/update-title` and `/api/update-description` endpoints.
- Auto-save only fires when:
  - A SKU is available (`currentSku` is set)
  - The field value differs from the last-persisted value (tracked via a ref)
  - The value is not empty
- On success, the persisted-value ref is updated so duplicate saves don't fire.
- On error, a toast is shown (see Part 2).

### Save Status Indicator

Replace the `isSavingTitle` / `isSavingDescription` booleans and the conditional Save buttons with a single `autoSaveStatus` state object:

```js
{ title: 'idle' | 'saving' | 'saved' | 'error', description: 'idle' | 'saving' | 'saved' | 'error' }
```

Render a small status hint inline near each field label:
- `idle` — nothing shown
- `saving` — `"Saving..."` in `text-text-muted text-xs`
- `saved` — `"Saved"` in `text-xs text-success`, clears back to idle after 2s
- `error` — not shown inline; error fires a toast instead (see Part 2)

### Files Changed

- **`App.jsx`** — add two `useEffect` hooks (one for `editableTitle`, one for `editableDescription`) that run debounced saves. Also add `autoSaveStatus` state and two "persisted value" refs to track what's currently on disk. Remove `isSavingTitle`, `isSavingDescription` states and their setters. Keep `handleSaveTitle` / `handleSaveDescription` as the actual save functions (called by the effects), but route their errors to toast instead of `setError`.
- **`CreateWorkflow.jsx`** — remove the "Save Title" and "Save Description" conditional buttons. Add the inline status hint near each field label. Pass `autoSaveStatus` as a prop.

### Mount Guard

The auto-save effects must not fire on initial mount or when a listing is first loaded. Use a `useRef` flag (`hasMountedTitle`, `hasMountedDescription`) that is set to `true` after the first render where the field is populated from `listingData`. The effect body checks this flag before scheduling the debounce.

---

## Part 2: Toast Notification System

### Architecture

Create **`frontend/src/components/ToastContainer.jsx`** — a new component that:
- Renders via `ReactDOM.createPortal` into `document.body`, completely outside the scroll tree.
- Displays a stack of toasts at `position: fixed; top: 1rem; left: 50%; transform: translateX(-50%); z-index: 9999` — centered at the top of the screen with a max-width of 480px.
- Each toast has: type (`success` | `error`), message string, optional detail string, and an id.

Toast state lives in `App.jsx`:
```js
const [toasts, setToasts] = useState([]);
const addToast = (type, message, detail) => {
  const id = Date.now();
  setToasts(prev => [...prev, { id, type, message, detail }]);
  return id;
};
const removeToast = (id) => setToasts(prev => prev.filter(t => t.id !== id));
```

**Auto-dismiss:**
- `success` toasts auto-dismiss after **4s**.
- `error` toasts **do not auto-dismiss** — the user must click the X to close them, since errors require attention.

`ToastContainer` is rendered once in `App.jsx` and receives `toasts` and `removeToast` as props.

### Toast Styling

- **Success:** `bg-success text-white` with a checkmark icon.
- **Error:** `bg-red-600 text-white` with an X icon.
- Each toast has a visible close button (X) at the top-right.
- If `detail` is provided, it renders in a smaller subtitle below the main message.
- Toasts stack vertically with `gap-2` — newest on top.

### Migration: Replace All Inline Error Rendering with Toasts

Every `setError(...)` call in `App.jsx` that is currently shown to the user via the inline renders in `CreateWorkflow.jsx` is replaced by `addToast('error', message)`. The global `error` state is removed entirely.

**Specific replacements:**

| Current call site | Replaces |
|---|---|
| `fetchListingPhotos` — validation + catch | `addToast('error', ...)` |
| `regenerateTitle` — API error + catch | `addToast('error', ...)` |
| `regenerateDescription` — API error + catch | `addToast('error', ...)` |
| `regenerateMetadata` — API error + catch | `addToast('error', ...)` |
| Image generation polling — partial + poll error | `addToast('error', ...)` |
| `handleRegenerateImages` — validation + catch | `addToast('error', ...)` |
| `handleTrimSelected` — catch | `addToast('error', ...)` |
| `handleAddNewVersions` — validation + catch | `addToast('error', ...)` |
| `handleCreateListing` — validation + catch | `addToast('error', ...)` |
| `handleTrimTitle` — catch | `addToast('error', ...)` |
| `handleSaveTitle` — catch (now also auto-save) | `addToast('error', ...)` |
| `handleSaveDescription` — catch (now also auto-save) | `addToast('error', ...)` |
| `fetchAllListings` — catch | `addToast('error', ...)` |
| `performRestock` — partial failure + catch | `addToast('error', ...)` |
| `handleUploadToEbay` — validation + catch | `addToast('error', ...)` |
| `handleTestingFunction` — catch | `addToast('error', ...)` |
| `handleListingClick` — catch | `addToast('error', ...)` |
| Auto-save title/description errors | `addToast('error', ...)` |

**The two inline error render blocks in `CreateWorkflow.jsx` (lines 191–193 and 196–200) are removed.** The `error` prop is removed from `CreateWorkflow`'s prop signature.

**The `MessageBarInput`'s `hasError` prop** (currently tied to the pre-submission error state) is removed or set permanently to `false` — the red border on the input is no longer needed since errors show as toasts.

**`ImageCanvas.jsx` native `alert()` calls** (lines 401 and 451) are replaced with `addToast('error', ...)`. Since `ImageCanvas` is a child of `App`, `addToast` is threaded down as a prop.

**Settings panel feedback** (`tokenMessage`, `appTokenResult`, `userTokenResult` in App.jsx; `message` in `ApiKeyManagementSection.jsx`) is **left as-is** — these are contextual inline results directly tied to the settings action the user just performed, not workflow errors. They don't need to be toasts.

### Upload Success Toasts

- The full green "Upload Successful!" card in `CreateWorkflow.jsx` is **kept** as-is — it's an informational result panel, not just a notification.
- The `CompactListingRow` inline success strip is also **kept** as-is.
- Both also fire a `addToast('success', 'Upload successful', 'View on eBay')` with a link in the detail, so the user gets top-of-screen confirmation regardless of scroll position.

---

## Part 3: Summary of All Files Changed

| File | Change |
|---|---|
| `frontend/src/App.jsx` | Add `toasts` state + `addToast`/`removeToast` helpers. Add `autoSaveStatus` state + `hasMountedTitle`/`hasMountedDescription` refs. Add two debounced-save `useEffect` hooks. Remove `error` state, `isSavingTitle`, `isSavingDescription`. Route all error paths to `addToast`. Thread `addToast` to `ImageCanvas` and `autoSaveStatus` to `CreateWorkflow`. |
| `frontend/src/components/ToastContainer.jsx` | New file. Portal-based fixed toast stack. |
| `frontend/src/components/CreateWorkflow.jsx` | Remove "Save Title" and "Save Description" buttons. Remove inline error renders (lines 191–200). Remove `error` prop. Add `autoSaveStatus` prop and inline status hints next to field labels. Remove `hasError` from `MessageBarInput` call. |
| `frontend/src/components/CompactListingRow.jsx` | No structural change; upload errors now appear via toast in App. |
| `frontend/src/components/ImageCanvas.jsx` | Replace two `alert(...)` calls with `addToast('error', ...)` via a new `onError` prop. |
| `frontend/src/components/ApiKeyManagementSection.jsx` | No change — inline settings feedback is kept. |

---

## Verification

1. **Auto-save:** Edit the title in the Create tab. After 800ms with no further typing, "Saving..." appears, then "Saved". Refresh the page and re-open the listing — the edited title should be persisted on disk without ever clicking a save button. Same for description.
2. **Upload reads live value:** Edit the title, wait for "Saved" to appear, then immediately click Upload. The uploaded listing should reflect the edited title.
3. **Toast on error:** Trigger an error (e.g. submit an invalid listing URL). A red toast should appear fixed at the top of the screen. No inline red box appears anywhere. The toast has an X to dismiss.
4. **Toast on upload success:** Upload a listing from the History tab while scrolled down. A green success toast appears at the top of the screen. The inline success strip in the row also appears.
5. **Error toast stays:** Error toasts don't auto-dismiss. Success toasts disappear after 4s.
6. **ImageCanvas errors:** Attempt to add an image with no images on canvas. Toast appears instead of native `alert()`.
