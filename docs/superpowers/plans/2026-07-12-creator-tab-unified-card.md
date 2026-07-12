# Creator Tab — Unified Listing Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Collapse the two-panel Create tab layout (top `ListingDetails` + bottom "Generated Listing") into a single unified card that leads with the generated title/description and provides a disclosure toggle for the original values.

**Architecture:** Delete `ListingDetails.jsx` (used only once). In `CreateWorkflow.jsx`, remove the `<ListingDetails>` block and replace the "Generated Listing" section with an expanded card that includes: a metadata row (badges for SKU/date/images/category + plain price), the existing editable title and description fields (locked while streaming), and a "View original title and description" disclosure below the description. Update `formatListingDateTime` in `listingDisplay.js` to output `MM/DD/YYYY, HH:MM`.

**Tech Stack:** React (Vite), Tailwind v4 with CSS variable tokens, `listingDisplay.js` utility functions.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `frontend/src/utils/listingDisplay.js` | Modify (line 17–29) | `formatListingDateTime` outputs `MM/DD/YYYY, HH:MM` |
| `frontend/src/components/CreateWorkflow.jsx` | Modify | Remove `ListingDetails` import + usage; add `showOriginal` state; add metadata row + disclosure to generated card; add `disabled` + muted style to title/description inputs while `isGeneratingText`; hide action buttons while generating |
| `frontend/src/components/ListingDetails.jsx` | Delete | No longer used anywhere |
| `docs/UI_VOCABULARY.md` | Modify | Update `listing-source-summary` entry to reflect new unified card |

---

## Task 1: Update `formatListingDateTime` to MM/DD/YYYY format

**Files:**
- Modify: `frontend/src/utils/listingDisplay.js:17-29`

- [ ] **Step 1: Replace the function body**

In `frontend/src/utils/listingDisplay.js`, replace lines 16–29 with:

```js
/** e.g. "07/11/2026, 14:43" — MM/DD/YYYY, local time 24 h. */
export function formatListingDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const yr = d.getFullYear();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${mo}/${day}/${yr}, ${hh}:${mm}`;
  } catch {
    return "—";
  }
}
```

- [ ] **Step 2: Verify the output manually**

Open a browser console (or Node) and run:
```js
const d = new Date("2026-07-11T14:43:00");
const mo = String(d.getMonth() + 1).padStart(2, "0");
const day = String(d.getDate()).padStart(2, "0");
console.log(`${mo}/${day}/${d.getFullYear()}, ${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`);
// expected: "07/11/2026, 14:43"
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/listingDisplay.js
git commit -m "fix: format listing date as MM/DD/YYYY, HH:MM"
```

---

## Task 2: Add `showOriginal` state and reset effect to `CreateWorkflow.jsx`

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:76-83`

- [ ] **Step 1: Add `showOriginal` state on line 77 (after `descriptionEditMode`)**

Change lines 76–83 from:
```jsx
  const [descriptionEditMode, setDescriptionEditMode] = useState(false);
  const [chatContext, setChatContext] = useState(DEFAULT_CHAT_CONTEXT);

  useEffect(() => {
    if (!listingLinkSubmitted) {
      setChatContext(DEFAULT_CHAT_CONTEXT);
    }
  }, [listingLinkSubmitted]);
```

To:
```jsx
  const [descriptionEditMode, setDescriptionEditMode] = useState(false);
  const [chatContext, setChatContext] = useState(DEFAULT_CHAT_CONTEXT);
  const [showOriginal, setShowOriginal] = useState(false);

  useEffect(() => {
    if (!listingLinkSubmitted) {
      setChatContext(DEFAULT_CHAT_CONTEXT);
      setShowOriginal(false);
    }
  }, [listingLinkSubmitted]);
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: add showOriginal state to CreateWorkflow"
```

---

## Task 3: Add `formatListingDateTime`, `formatPrice`, `formatCategoryShort` imports to `CreateWorkflow.jsx`

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:1-14`

- [ ] **Step 1: Add the import**

After line 14 (after `import { DEFAULT_CHAT_CONTEXT, ... } from "../constants/chatContextModes";`), add:

```jsx
import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: import listingDisplay utils into CreateWorkflow"
```

---

## Task 4: Replace `<ListingDetails>` block with unified card metadata row

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:186-190`

The current block (lines 186–190):
```jsx
      {listingLinkSubmitted && listing && (
        <div className="mt-4">
          <ListingDetails listing={listing} photos={photos} sku={currentSku} />
        </div>
      )}
```

- [ ] **Step 1: Remove the `<ListingDetails>` block entirely**

Delete lines 186–190. The metadata row will be added inside the "Generated Listing" card in Task 5. Nothing should render in its place here.

- [ ] **Step 2: Remove the `ListingDetails` import on line 6**

Delete:
```jsx
import ListingDetails from "./ListingDetails";
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "refactor: remove ListingDetails from CreateWorkflow"
```

---

## Task 5: Add metadata row to the generated listing card

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:324-329`

The current generated listing card opens (lines 324–329):
```jsx
      {listing && (isGeneratingText || editableTitle !== "") && (
        <div className="mt-8">
          <h2 className="mb-4 text-xl font-semibold text-text-primary">
            {isGeneratingText ? "Writing Listing..." : "Generated Listing"}
          </h2>
          <div className="space-y-4">
```

- [ ] **Step 1: Replace those lines with the version that includes the metadata row**

```jsx
      {listing && (isGeneratingText || editableTitle !== "") && (
        <div className="mt-8 rounded-xl border border-border-default bg-surface-panel px-4 pb-4 pt-5 shadow-sm sm:px-5 sm:pb-5 sm:pt-6">
          {/* Metadata row */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {currentSku && (
                <span className="rounded-md border border-border-default px-2 py-0.5 font-mono text-xs text-text-muted">
                  {currentSku}
                </span>
              )}
              {listing.itemCreationDate && (
                <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                  {formatListingDateTime(listing.itemCreationDate)}
                </span>
              )}
              <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                {generatedImages?.length ?? 0}{" "}
                {(generatedImages?.length ?? 0) === 1 ? "image" : "images"}
              </span>
              {listing.categoryId != null && (
                <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                  Cat {formatCategoryShort(listing.categoryId)}
                </span>
              )}
            </div>
            <div className="shrink-0 text-xl font-bold text-text-primary">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
          <div className="space-y-4">
```

- [ ] **Step 2: Close the new outer `<div>` at the bottom of the card**

Find the closing of the old `<div className="mt-8">` card. Currently line 574–575 reads:
```jsx
        </div>
      )}
```

This closes `<div className="mt-8">` and the `{listing && ...}` condition. Since we added one extra wrapping `<div>` (the card container), the closing count is unchanged — the existing two closing tags still close the `space-y-4` div and the outer card `div`. No change needed here.

- [ ] **Step 3: Verify in browser that the metadata row renders above the title field and the card has a border/background**

Run `npm run dev` and submit a listing URL. The metadata row should appear at the top of the card with badged SKU, date, image count, category, and plain price on the right.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: add metadata row to unified listing card"
```

---

## Task 6: Lock title and description inputs while `isGeneratingText`

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx` — the title `<input>` (around line 359) and description `<textarea>` (around line 418)

- [ ] **Step 1: Add `disabled` and muted style to the title `<input>`**

Find the title `<input>` (currently around line 359–369). Change:
```jsx
              <input
                type="text"
                className={`w-full rounded-lg border-2 px-3 py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  editableTitle?.length > 80
                    ? "border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500/20"
                    : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                }`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange(e.target.value)}
                placeholder="Listing title..."
              />
```

To:
```jsx
              <input
                type="text"
                className={`w-full rounded-lg border-2 px-3 py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  isGeneratingText
                    ? "cursor-not-allowed border-border-default bg-surface-muted text-text-muted opacity-60"
                    : editableTitle?.length > 80
                      ? "border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500/20"
                      : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                }`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange(e.target.value)}
                placeholder="Listing title..."
                disabled={isGeneratingText}
              />
```

- [ ] **Step 2: Hide "AI Trim" and "Save Title" buttons while generating**

Find the button group (currently around lines 381–404):
```jsx
              <div className="flex gap-2">
                {editableTitle?.length > 80 && (
                  <button
                    type="button"
                    className={btnPillSm}
                    onClick={onTrimTitle}
                    disabled={isTrimmingTitle}
                  >
                    {isTrimmingTitle ? "Trimming..." : "AI Trim Title"}
                  </button>
                )}
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
              </div>
```

Replace with:
```jsx
              {!isGeneratingText && (
                <div className="flex gap-2">
                  {editableTitle?.length > 80 && (
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onTrimTitle}
                      disabled={isTrimmingTitle}
                    >
                      {isTrimmingTitle ? "Trimming..." : "AI Trim Title"}
                    </button>
                  )}
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
                </div>
              )}
```

- [ ] **Step 3: Add `disabled` and muted style to the description `<textarea>`**

Find the `<textarea>` (currently around lines 418–426). Change:
```jsx
                <textarea
                  className="mt-2 min-h-[200px] w-full resize-y rounded-lg border-2 border-border-default bg-surface-panel p-3 font-mono text-sm text-text-primary transition-colors focus:border-primary focus:outline-none"
                  value={editableDescription}
                  onChange={(e) => onEditableDescriptionChange(e.target.value)}
                  placeholder="HTML description..."
                  rows={12}
                  spellCheck={false}
                />
```

To:
```jsx
                <textarea
                  className={`mt-2 min-h-[200px] w-full resize-y rounded-lg border-2 p-3 font-mono text-sm transition-colors focus:outline-none ${
                    isGeneratingText
                      ? "cursor-not-allowed border-border-default bg-surface-muted text-text-muted opacity-60"
                      : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                  }`}
                  value={editableDescription}
                  onChange={(e) => onEditableDescriptionChange(e.target.value)}
                  placeholder="HTML description..."
                  rows={12}
                  spellCheck={false}
                  disabled={isGeneratingText}
                />
```

- [ ] **Step 4: Hide "Save Description" button while generating**

Find (currently around lines 436–449):
```jsx
              <div className="mt-2 flex gap-2">
                {listingData &&
                  editableDescription !==
                    (listingData.inventoryItem?.product?.description || "") && (
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onSaveDescription}
                      disabled={isSavingDescription}
                    >
                      {isSavingDescription ? "Saving..." : "Save Description"}
                    </button>
                  )}
              </div>
```

Replace with:
```jsx
              {!isGeneratingText && (
                <div className="mt-2 flex gap-2">
                  {listingData &&
                    editableDescription !==
                      (listingData.inventoryItem?.product?.description || "") && (
                      <button
                        type="button"
                        className={btnPillSm}
                        onClick={onSaveDescription}
                        disabled={isSavingDescription}
                      >
                        {isSavingDescription ? "Saving..." : "Save Description"}
                      </button>
                    )}
                </div>
              )}
```

- [ ] **Step 5: Also disable the "Edit HTML" / "Preview HTML" toggle button while generating**

Find (currently around lines 409–415):
```jsx
                <button
                  type="button"
                  className="rounded-lg border-2 border-border-default bg-surface-panel px-3 py-1.5 text-sm font-semibold text-text-primary transition-colors hover:border-primary hover:text-primary"
                  onClick={() => setDescriptionEditMode((v) => !v)}
                >
                  {descriptionEditMode ? "Preview HTML" : "Edit HTML"}
                </button>
```

Replace with:
```jsx
                {!isGeneratingText && (
                  <button
                    type="button"
                    className="rounded-lg border-2 border-border-default bg-surface-panel px-3 py-1.5 text-sm font-semibold text-text-primary transition-colors hover:border-primary hover:text-primary"
                    onClick={() => setDescriptionEditMode((v) => !v)}
                  >
                    {descriptionEditMode ? "Preview HTML" : "Edit HTML"}
                  </button>
                )}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: lock title/description inputs and hide action buttons while generating"
```

---

## Task 7: Add "View original title and description" disclosure

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx` — after the description `</div>` (end of description section, around line 450) and before `{isCreatingListing && ...}`

- [ ] **Step 1: Add the disclosure after the closing `</div>` of the description `border-b` block**

Find the closing of the description section. It currently ends around line 450:
```jsx
            </div>
          </div>
```
(The first `</div>` closes `border-b border-border-default pb-4`, the second closes `space-y-4`.)

Insert the disclosure **inside** `space-y-4`, after the description `border-b` block but before `</div>` that closes `space-y-4`:

```jsx
            {/* Original title/description disclosure */}
            <div>
              <button
                type="button"
                className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
                onClick={() => setShowOriginal((v) => !v)}
              >
                <span>{showOriginal ? "▼" : "▶"}</span>
                <span>
                  {showOriginal
                    ? "Hide original title and description"
                    : "View original title and description"}
                </span>
              </button>
              {showOriginal && (
                <div className="mt-3 space-y-2">
                  <p className="text-sm font-semibold text-text-primary">
                    {listing.title || "No title"}
                  </p>
                  {listing.description &&
                    listing.description.trim() !== "" &&
                    listing.description !== "No description available" && (
                      <div className="max-h-[calc(1.625em*6)] overflow-y-auto overscroll-contain rounded-lg border border-border-default bg-surface-muted p-3">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                          {listing.description.trim()}
                        </p>
                      </div>
                    )}
                </div>
              )}
            </div>
```

- [ ] **Step 2: Verify the disclosure works in browser**

Run `npm run dev`, submit a listing URL, wait for text generation to complete, then:
1. The card shows generated title + description with no original content visible.
2. Clicking "▶ View original title and description" expands to show the original title (plain text) and original description (scrollable box).
3. Clicking again ("▼ Hide original title and description") collapses it.
4. Submitting a new listing URL resets `showOriginal` to false (collapsed).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: add original title/description disclosure toggle"
```

---

## Task 8: Delete `ListingDetails.jsx`

**Files:**
- Delete: `frontend/src/components/ListingDetails.jsx`

- [ ] **Step 1: Confirm no remaining imports**

Run from project root:
```bash
grep -r "ListingDetails" frontend/src/
```
Expected output: nothing (zero matches). If any match remains, remove that import first.

- [ ] **Step 2: Delete the file**

```bash
git rm frontend/src/components/ListingDetails.jsx
```

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor: delete ListingDetails component (merged into unified card)"
```

---

## Task 9: Update `UI_VOCABULARY.md`

**Files:**
- Modify: `docs/UI_VOCABULARY.md`

- [ ] **Step 1: Update the `listing-source-summary` entry**

Find the `listing-source-summary` row in the table. Replace its description to reflect the new unified card:

| Reference ID | Short name | When | What the user sees |
|---|---|---|---|
| `listing-generated-card` | Generated listing card | After link submit, once `listing` is set and text generation begins | Single unified card: metadata row (badged SKU, date, live image count, category + right-aligned price), editable title (locked while streaming), editable description (locked while streaming), "View original title and description" disclosure at bottom. Replaces the old two-panel `ListingDetails` + "Generated Listing" layout. |

Also update the **Files** section under that entry to remove `ListingDetails.jsx`.

- [ ] **Step 2: Commit**

```bash
git add docs/UI_VOCABULARY.md
git commit -m "docs: update UI_VOCABULARY for unified listing card"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|---|---|
| Generated title/description shown by default | Task 5 (card structure), Task 6 (inputs always present) |
| Metadata row: SKU, date (MM/DD/YYYY), image count (live), category, price (right-aligned, no badge) | Tasks 1, 5 |
| Badge style for SKU/date/images/category | Task 5 |
| Price not duplicated (plain, right-aligned only) | Task 5 |
| `generatedImages.length` for live image count | Task 5 |
| Title/description inputs locked while `isGeneratingText` | Task 6 |
| Action buttons hidden while generating | Task 6 |
| "View original" disclosure with toggle label | Task 7 |
| Original title plain text, description in scrollable box | Task 7 |
| `showOriginal` resets on new listing | Task 2 |
| `ListingDetails.jsx` deleted | Tasks 4, 8 |
| `formatListingDateTime` outputs MM/DD/YYYY | Task 1 |
| `UI_VOCABULARY.md` updated | Task 9 |

**Placeholder scan:** None found — every step has concrete code.

**Type consistency:** `formatListingDateTime`, `formatPrice`, `formatCategoryShort` defined in Task 1/3 and used identically in Task 5. `showOriginal` / `setShowOriginal` defined in Task 2 and used in Tasks 7. `isGeneratingText` is an existing prop, used consistently throughout Tasks 6–7.

**Note on `listingData` block:** The existing `listingData` detail block (SKU, price from eBay API object, image URLs list, created date) below the description is intentionally left unchanged. It shows post-confirm draft data from a different source than the metadata row.
