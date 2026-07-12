# Chat Bar AI Editing — Design Spec

**Date:** 2026-07-12

## Overview

After a listing link is submitted, the input bar moves to the bottom of the screen and is repurposed as a context-aware AI editing prompt. The user selects a context (Title, Description, Photos, Metadata) from the `ChatContextSelector` dropdown, types a prompt, and presses Enter. The input is cleared immediately and the appropriate AI action fires.

---

## 1. Input Clear on Submit

**Current behavior:** The bottom bar's form `onSubmit` calls `handleSubmit` → `fetchListingPhotos()`. This path only applies pre-link.

**New behavior:** In `CreateWorkflow.jsx`, the form `onSubmit` branches on `listingLinkSubmitted`:
- `false` → existing `onSubmit` (fetches listing photos, sets `listingLinkSubmitted = true`)
- `true` → captures the current `listingId` value, calls `setListingId("")` to clear the input, then calls `onChatSubmit(prompt, chatContext)` passed from `App.jsx`

`onChatSubmit` is a new prop on `CreateWorkflow`. In `App.jsx`, `handleChatSubmit(prompt, context)` dispatches to the correct handler:

```
"title"       → regenerateTitle(prompt)
"description" → regenerateDescription(prompt)
"photos"      → enterPhotoSelectionMode(prompt)
"metadata"    → regenerateMetadata(prompt)
```

---

## 2. Title Regeneration

**Trigger:** `chatContext === "title"` + user submits prompt.

**Backend:** `POST /api/regenerate-title`
- Request body: `{ sku, current_title, user_prompt, model }`
- `current_title` is `editableTitle` (the already-AI-edited value, never the original source listing)
- Backend: passes `current_title` + `user_prompt` to the text LLM; returns `{ title: string }`
- No streaming — single JSON response

**Frontend:**
- New loading flag: `isRegeneratingTitle` (shown as spinner/disabled state on the bar)
- On success: `setEditableTitle(data.title)`; also patch `listingData` in place (same pattern as `handleTrimTitle`)
- On error: show error toast, leave `editableTitle` unchanged

---

## 3. Description Regeneration

**Trigger:** `chatContext === "description"` + user submits prompt.

**Backend:** `POST /api/regenerate-description`
- Request body: `{ sku, current_description, user_prompt, model }`
- `current_description` is `editableDescription` (HTML string, already AI-edited)
- Backend: passes `current_description` + `user_prompt` to the text LLM; returns `{ description: string }`
- No streaming — single JSON response

**Frontend:**
- New loading flag: `isRegeneratingDescription`
- On success: `setEditableDescription(data.description)`; patch `listingData` in place
- On error: show error toast, leave `editableDescription` unchanged

---

## 4. Photos — Selection Mode + Targeted Regeneration

**Trigger:** `chatContext === "photos"` + user submits prompt.

**Two sub-cases:**

### 4a. No generated images yet (image generation hasn't run)
Does not apply — Photos context is only meaningful after images have been generated. If no generated images exist, treat as a no-op or show a status message.

### 4b. Generated images exist
1. Enter **selection mode** on the generated images grid:
   - All generated images are auto-selected (checked)
   - User can uncheck images they want to keep as-is
   - The submitted prompt is stored in a new state variable `pendingPhotoPrompt`
2. A "Regenerate Selected" confirm button appears in the grid UI
3. On confirm: send only the checked images + `pendingPhotoPrompt` to re-run image generation for those slots
   - Reuses existing image generation logic but scoped to selected indices
   - Unselected images are left unchanged
4. On complete: selection mode exits, `pendingPhotoPrompt` is cleared

**New state in App.jsx:**
- `photoSelectionMode: boolean` (default `false`)
- `selectedPhotoIndices: Set<number>` (indices into `generatedImages`)
- `pendingPhotoPrompt: string`

**Props passed to CreateWorkflow / image grid:**
- `photoSelectionMode`, `selectedPhotoIndices`, `onTogglePhotoSelection`, `pendingPhotoPrompt`, `onConfirmPhotoRegeneration`

---

## 5. Metadata Regeneration

**Trigger:** `chatContext === "metadata"` + user submits prompt.

**What "metadata" is:** The listing JSON fields needed for eBay upload (item specifics: brand, color, condition, MPN, etc.). Fields not needed for upload (internal SKU bookkeeping, etc.) are stripped before sending to the LLM.

**Backend:** `POST /api/regenerate-metadata`
- Request body: `{ sku, user_prompt }`
- Backend:
  1. Loads `Generated_Listings/<sku>.json`
  2. Extracts only eBay-upload-relevant fields into a clean JSON object
  3. Builds prompt: `<JSON>\n\nPlease edit the JSON according to this instruction and keep it in JSON format.\n\n<user_prompt>`
  4. Sends to text LLM, parses JSON from response
  5. Merges updated fields back into the draft listing file
  6. Returns `{ metadata: object }` — the updated relevant fields
- No streaming — single JSON response

**Frontend:**
- New loading flag: `isRegeneratingMetadata`
- On success: update the relevant fields in `listingData` in place so the metadata display re-renders
- On error: show error toast, leave metadata unchanged

**Format safety:** The backend wraps JSON parsing in a try/catch; if the LLM returns malformed JSON, return a `400` error with a human-readable message so the frontend can surface it.

---

## 6. Pre-link vs Post-link Submit Disambiguation

The form `onSubmit` in `CreateWorkflow.jsx` already fires for both states via the same `<form>`. The branch is:

```js
if (!listingLinkSubmitted) {
  onSubmit(e);          // existing: fetch listing photos
} else {
  e.preventDefault();
  const prompt = listingId.trim();
  if (!prompt) return;
  setListingId("");
  onChatSubmit(prompt, chatContext);
}
```

This keeps the pre-link path untouched.

---

## 7. Test Workflow Mirror

The test-workflow tab in `App.jsx` maintains parallel state (`testListingLinkSubmitted`, `testListingId`, etc.). For each new handler (`regenerateTitle`, `regenerateDescription`, `enterPhotoSelectionMode`, `regenerateMetadata`), a corresponding `test*` mock handler must be added that simulates the action with a `setTimeout` and mock data — same pattern as existing test handlers.

---

## 8. Files Changed

| File | Change |
|---|---|
| `frontend/src/App.jsx` | Add `handleChatSubmit`, `regenerateTitle`, `regenerateDescription`, `enterPhotoSelectionMode`, `regenerateMetadata`; new state flags; new props to CreateWorkflow; test-workflow mirrors |
| `frontend/src/components/CreateWorkflow.jsx` | Branch form `onSubmit` on `listingLinkSubmitted`; pass `onChatSubmit` prop; wire photo selection mode UI |
| `app.py` | Add `POST /api/regenerate-title`, `POST /api/regenerate-description`, `POST /api/regenerate-metadata` routes |
| `backend/text_models.py` | No change (existing `call_text_llm` interface reused) |
| `backend/copyScripts/combine_data.py` | Add helper to extract upload-relevant metadata fields from a draft listing JSON |

---

## 9. Out of Scope

- Streaming responses for title/description/metadata regeneration (single-response is sufficient)
- Undo/history for regenerated values
- Regenerating photos that were never generated (no-op)
- Changes to the pre-link submit flow
