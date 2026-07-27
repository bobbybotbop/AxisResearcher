# History Compact View Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact view mode to the History tab that becomes the new default, showing a fixed-height hero image + upload button with no description or thumbnail strip, toggled via a new icon button in the toolbar.

**Architecture:** A new `CompactListingRow` component mirrors `GeneratedListingCard` but replaces `aspect-square` with `h-24` and removes the description panel and `RestGalleryStrip`. A `historyViewMode` state in `App.jsx` (localStorage-persisted, default `"compact"`) controls which component renders in the listing loop. `UploadListingsToolbar` receives two new props to render the toggle button.

**Tech Stack:** React, lucide-react (LayoutList / LayoutGrid icons), Tailwind v4 semantic tokens, localStorage

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Create | `frontend/src/components/CompactListingRow.jsx` | New compact card component |
| Modify | `frontend/src/components/UploadListingsToolbar.jsx` | Add viewMode toggle button + 2 new props |
| Modify | `frontend/src/App.jsx` | Add state, import, prop pass-through, branched render |

---

### Task 1: Create `CompactListingRow`

**Files:**
- Create: `frontend/src/components/CompactListingRow.jsx`

- [ ] **Step 1: Create the file with the full component**

`frontend/src/components/CompactListingRow.jsx`:

```jsx
import { useState } from "react";
import { btnPill } from "../styles/buttonPill";
import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";

export default function CompactListingRow({
  listing,
  onCardClick,
  onUpload,
  isUploading,
  uploadResult,
  quantity,
  loadingQuantity,
}) {
  const urls = Array.isArray(listing.imageUrls) ? listing.imageUrls : [];
  const [imageIndex, setImageIndex] = useState(0);

  const safeIndex = urls.length ? imageIndex % urls.length : 0;
  const title = listing.title || "No title";
  const imageCount = listing.imageCount ?? urls.length ?? 0;
  const categoryId = String(listing.categoryId ?? "—");
  const categoryShort = formatCategoryShort(listing.categoryId);

  const ebayListingId = String(listing.ebayListingId ?? "").trim();
  const ebayItemUrl = ebayListingId
    ? `https://www.ebay.com/itm/${ebayListingId}`
    : "";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onCardClick?.(listing)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardClick?.(listing);
        }
      }}
      className="flex w-full cursor-pointer flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md md:flex-row md:items-stretch"
    >
      {/* Image column — fixed h-24 hero + upload button */}
      <div className="flex w-full shrink-0 flex-col border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r md:border-border-default">
        <div className="relative w-full">
          <div className="h-24 w-full bg-surface-muted">
            {urls.length > 0 ? (
              <div className="flex h-full w-full items-center justify-center">
                <img
                  src={urls[safeIndex]}
                  alt={title}
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-text-muted">
                No image
              </div>
            )}
          </div>
          {urls.length > 1 && (
            <div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1.5">
              {urls.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  aria-label={`Show image ${i + 1}`}
                  className={`h-1.5 w-1.5 rounded-full ring-1 ring-white ring-offset-0 transition-all ${
                    i === safeIndex
                      ? "w-4 bg-black"
                      : "bg-black/50 hover:bg-black/80"
                  }`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setImageIndex(i);
                  }}
                />
              ))}
            </div>
          )}
        </div>
        <div
          className="border-t border-border-default bg-surface-panel p-2 sm:p-3"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <div className="flex flex-col gap-2">
            {ebayItemUrl ? (
              <a
                href={ebayItemUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex w-full items-center justify-center no-underline ${btnPill}`}
                onClick={(e) => e.stopPropagation()}
              >
                View on eBay
              </a>
            ) : (
              <button
                type="button"
                className={`w-full ${btnPill} disabled:transform-none`}
                onClick={() => onUpload?.(listing)}
                disabled={isUploading}
              >
                {isUploading ? "Uploading..." : "Upload to eBay"}
              </button>
            )}
            {uploadResult && (
              <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-white p-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-green-700 bg-white text-sm font-bold text-green-800">
                  ✓
                </div>
                <div className="min-w-0 flex-1 text-xs text-text-primary">
                  {uploadResult.listingId && (
                    <a
                      href={`https://www.ebay.com/itm/${uploadResult.listingId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold text-primary underline hover:no-underline"
                    >
                      {uploadResult.listingId}
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content column — title + meta only, no description, no gallery strip */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-2 p-3 sm:p-4">
        <div className="flex shrink-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-1 text-base font-semibold leading-snug text-text-primary">
              {title}
            </h3>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm text-text-muted">
              <span className="font-mono text-text-muted">{listing.sku}</span>
              {listing.createdDateTime && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>{formatListingDateTime(listing.createdDateTime)}</span>
                </>
              )}
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap"
                title="Number of images on the listing"
              >
                {imageCount} {imageCount === 1 ? "image" : "images"}
              </span>
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap font-medium text-text-muted"
                title={
                  categoryId !== "—" ? `Category ID: ${categoryId}` : undefined
                }
              >
                {categoryShort === "—" ? "—" : `Cat ${categoryShort}`}
              </span>
              {String(listing.ebayListingId ?? "").trim() ? (
                <>
                  <span className="text-text-muted">·</span>
                  {quantity != null ? (
                    <span
                      className="whitespace-nowrap"
                      title="Live eBay stock quantity"
                    >
                      Qty: {quantity}
                    </span>
                  ) : loadingQuantity ? (
                    <span
                      className="inline-flex items-center gap-1 whitespace-nowrap text-text-muted"
                      title="Loading quantity"
                    >
                      Qty:{" "}
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent opacity-50" />
                    </span>
                  ) : (
                    <span
                      className="whitespace-nowrap text-text-muted"
                      title="Quantity unavailable"
                    >
                      Qty: —
                    </span>
                  )}
                </>
              ) : null}
            </p>
          </div>
          <div className="shrink-0 text-left sm:text-right">
            <div className="text-lg font-bold text-text-primary">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/CompactListingRow.jsx
git commit -m "feat: add CompactListingRow component"
```

---

### Task 2: Add view mode toggle to `UploadListingsToolbar`

**Files:**
- Modify: `frontend/src/components/UploadListingsToolbar.jsx`

- [ ] **Step 1: Add `LayoutList` and `LayoutGrid` to the lucide-react import at the top of the file**

Current line 3:
```js
import { RefreshCw } from "lucide-react";
```

Replace with:
```js
import { RefreshCw, LayoutList, LayoutGrid } from "lucide-react";
```

- [ ] **Step 2: Add the two new props to the function signature**

Current:
```js
export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
  showUnuploadedListings,
  onShowUnuploadedListingsChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  onRefresh,
  isRefreshing,
  autoRestockEnabled,
  autoRestockQuantity,
  onAutoRestockEnabledChange,
  onAutoRestockQuantityChange,
  onManualRestock,
  isRestocking,
}) {
```

Replace with:
```js
export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
  showUnuploadedListings,
  onShowUnuploadedListingsChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  onRefresh,
  isRefreshing,
  autoRestockEnabled,
  autoRestockQuantity,
  onAutoRestockEnabledChange,
  onAutoRestockQuantityChange,
  onManualRestock,
  isRestocking,
  viewMode,
  onViewModeChange,
}) {
```

- [ ] **Step 3: Insert the toggle button between the Filter button's closing `</div>` and the Auto-restock group**

Locate the comment `{/* Auto-restock: far right */}` (around line 203 in the original file). Insert the following block immediately before it:

```jsx
      {/* View mode toggle */}
      <button
        type="button"
        aria-label={
          viewMode === "compact" ? "Switch to detailed view" : "Switch to compact view"
        }
        title={
          viewMode === "compact" ? "Switch to detailed view" : "Switch to compact view"
        }
        onClick={() =>
          onViewModeChange(viewMode === "compact" ? "detailed" : "compact")
        }
        className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-border-default shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40 ${
          viewMode === "compact"
            ? "bg-surface-muted text-text-primary hover:bg-surface-hover"
            : "bg-surface-panel text-text-primary hover:bg-surface-hover"
        }`}
      >
        {viewMode === "compact" ? (
          <LayoutList size={20} aria-hidden />
        ) : (
          <LayoutGrid size={20} aria-hidden />
        )}
      </button>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UploadListingsToolbar.jsx
git commit -m "feat: add view mode toggle button to UploadListingsToolbar"
```

---

### Task 3: Wire `historyViewMode` state in `App.jsx`

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add the `CompactListingRow` import**

After the existing import on line 13:
```js
import GeneratedListingCard from "./components/GeneratedListingCard";
```

Add:
```js
import CompactListingRow from "./components/CompactListingRow";
```

- [ ] **Step 2: Add the `historyViewMode` state**

Find the block of `useState` declarations near the other history-related state (around line 349 where `historyPage` is declared). Add this after `historyPageSize`:

```js
const [historyViewMode, setHistoryViewMode] = useState(() => {
  const stored = localStorage.getItem("axisHistoryViewMode");
  return stored === "detailed" ? "detailed" : "compact";
});
```

- [ ] **Step 3: Add the `handleHistoryViewModeChange` handler**

Find `handleTabChange` (around line 2176). Add this immediately before it:

```js
const handleHistoryViewModeChange = (mode) => {
  setHistoryViewMode(mode);
  localStorage.setItem("axisHistoryViewMode", mode);
};
```

- [ ] **Step 4: Pass the new props to `UploadListingsToolbar`**

Locate the `<UploadListingsToolbar` usage (around line 2997). Add two props at the end of the prop list, before the closing `/>`:

```jsx
                viewMode={historyViewMode}
                onViewModeChange={handleHistoryViewModeChange}
```

- [ ] **Step 5: Branch the render at `paginatedListings.map`**

Locate this block (around line 3037):

```jsx
                  <div className="flex flex-col gap-4">
                    {paginatedListings.map((listing) => (
                      <GeneratedListingCard
                        key={listing.sku}
                        listing={listing}
                        onCardClick={handleListingClick}
                        onUpload={(l) => handleUploadToEbay(l.sku, l)}
                        isUploading={uploadingSkus.has(listing.sku)}
                        uploadResult={uploadResults[listing.sku]}
                        quantity={listingQuantities[listing.sku]}
                        loadingQuantity={loadingQuantities}
                      />
                    ))}
                  </div>
```

Replace with:

```jsx
                  <div className="flex flex-col gap-4">
                    {paginatedListings.map((listing) =>
                      historyViewMode === "compact" ? (
                        <CompactListingRow
                          key={listing.sku}
                          listing={listing}
                          onCardClick={handleListingClick}
                          onUpload={(l) => handleUploadToEbay(l.sku, l)}
                          isUploading={uploadingSkus.has(listing.sku)}
                          uploadResult={uploadResults[listing.sku]}
                          quantity={listingQuantities[listing.sku]}
                          loadingQuantity={loadingQuantities}
                        />
                      ) : (
                        <GeneratedListingCard
                          key={listing.sku}
                          listing={listing}
                          onCardClick={handleListingClick}
                          onUpload={(l) => handleUploadToEbay(l.sku, l)}
                          isUploading={uploadingSkus.has(listing.sku)}
                          uploadResult={uploadResults[listing.sku]}
                          quantity={listingQuantities[listing.sku]}
                          loadingQuantity={loadingQuantities}
                        />
                      )
                    )}
                  </div>
```

- [ ] **Step 6: Verify the app runs correctly**

Run the dev server:
```bash
npm run dev
```

Navigate to `http://localhost:4000/history`. Verify:
- History tab loads with compact rows by default (h-24 hero, no description, no thumbnail strip)
- The toolbar shows a `LayoutList` icon button between the Filter button and Auto-restock group, with a filled (`bg-surface-muted`) background indicating compact is active
- Clicking the toggle button switches to detailed view: cards expand to full height with description panel and thumbnail strip; button switches to `LayoutGrid` icon with plain `bg-surface-panel` background
- Toggling back to compact restores the short rows
- Refreshing the page preserves the last-used mode (localStorage)
- Clicking a compact row opens the detail modal as before

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire historyViewMode state and compact/detailed render branch"
```
