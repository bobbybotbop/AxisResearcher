# History Tab: Live Quantity + Pagination Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch live eBay stock quantity for each published listing, display it in the History tab card metadata row, add pagination (10/25/50 per page), and a manual refresh button — with quantities auto-fetched once on initial app load.

**Architecture:** New `POST /api/listings/quantities` backend endpoint calls eBay's Sell Inventory API per SKU using the stored user token. The frontend adds `historyPage`, `historyPageSize`, and `listingQuantities` state; a `useRef` flag prevents re-fetching on tab switches. `GeneratedListingCard` gains a `quantity` prop rendered in the existing metadata pill row.

**Tech Stack:** Flask (Python), React (Vite), eBay Sell Inventory API v1, lucide-react for icons, Tailwind v4 CSS tokens

---

## File Map

- **Modify:** `app.py` — add `POST /api/listings/quantities` endpoint
- **Modify:** `frontend/src/App.jsx` — add state, fetch logic, paginated rendering, pagination controls
- **Modify:** `frontend/src/components/GeneratedListingCard.jsx` — accept and render `quantity` prop
- **Modify:** `frontend/src/components/UploadListingsToolbar.jsx` — add refresh button prop

---

## Task 1: Backend — `POST /api/listings/quantities`

**Files:**
- Modify: `app.py` (add after `_test_user_token` block, around line 1403)

- [ ] **Step 1: Add the endpoint to `app.py`**

Add this block after the `api_test_user_token` route (after line ~1402):

```python
@app.route('/api/listings/quantities', methods=['POST'])
def api_listings_quantities():
    """Fetch live eBay inventory quantity for a list of SKUs."""
    body = request.get_json(silent=True) or {}
    skus = body.get('skus', [])
    if not skus:
        return jsonify({}), 200

    token = os.getenv('user_token', '').strip()
    if not token:
        return jsonify({sku: None for sku in skus}), 200

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }

    result = {}
    for sku in skus:
        try:
            url = f'https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}'
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                qty = (
                    data.get('availability', {})
                        .get('shipToLocationAvailability', {})
                        .get('quantity')
                )
                result[sku] = qty
            else:
                result[sku] = None
        except Exception:
            result[sku] = None

    return jsonify(result), 200
```

- [ ] **Step 2: Verify endpoint manually**

Start the backend: `npm run dev:backend`

Run in a new terminal (replace `SKU-001` with a real SKU from your `Generated_Listings/` directory and ensure `user_token` is set in `.env`):

```bash
curl -s -X POST http://localhost:5000/api/listings/quantities \
  -H "Content-Type: application/json" \
  -d '{"skus": ["SKU-001"]}' | python -m json.tool
```

Expected: `{"SKU-001": <number or null>}` — no 500 error.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add POST /api/listings/quantities endpoint"
```

---

## Task 2: Frontend state + fetch logic in `App.jsx`

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add new state variables**

Find the block of `useState` declarations for the upload/history tab (around line 267–278). Add after `const [loadingListingDetail, setLoadingListingDetail] = useState(false);`:

```jsx
const [historyPage, setHistoryPage] = useState(0);
const [historyPageSize, setHistoryPageSize] = useState(10);
const [listingQuantities, setListingQuantities] = useState({});
const [loadingQuantities, setLoadingQuantities] = useState(false);
const quantitiesFetchedRef = useRef(false);
```

(`useRef` is already imported on line 1.)

- [ ] **Step 2: Add `fetchQuantitiesForPage` function**

Add this function directly after `fetchAllListings` (after line ~1431):

```jsx
const fetchQuantitiesForPage = async (listings) => {
  const skus = listings
    .filter((l) => String(l.ebayListingId ?? "").trim())
    .map((l) => l.sku);
  if (!skus.length) return;

  setLoadingQuantities(true);
  try {
    const res = await fetch("/api/listings/quantities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ skus }),
    });
    if (!res.ok) return;
    const data = await res.json();
    setListingQuantities((prev) => ({ ...prev, ...data }));
  } catch {
    // silently ignore — quantities are non-critical
  } finally {
    setLoadingQuantities(false);
  }
};
```

- [ ] **Step 3: Add one-time auto-fetch on mount**

Add this `useEffect` after the existing tab-entry effects (after line ~1550):

```jsx
// Fetch quantities once on first mount, not on every tab visit.
useEffect(() => {
  if (quantitiesFetchedRef.current) return;
  quantitiesFetchedRef.current = true;
  // Wait until listings are loaded before fetching quantities.
  // We trigger this from within fetchAllListings below.
}, []);
```

- [ ] **Step 4: Auto-fetch quantities after initial load**

Modify `fetchAllListings` to trigger quantity fetch only the first time. Replace:

```jsx
      setAllListings(data.listings || []);
      console.log("Loaded listings:", data.listings);
```

With:

```jsx
      const listings = data.listings || [];
      setAllListings(listings);
      console.log("Loaded listings:", listings);
      if (!quantitiesFetchedRef.current) {
        quantitiesFetchedRef.current = true;
        fetchQuantitiesForPage(listings);
      }
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add quantity state and one-time auto-fetch in App.jsx"
```

---

## Task 3: Pagination state + derived values + reset on filter change

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add paginated slice derived value**

Find the `filteredUploadListings` `useMemo` block (around line 610). After it, add:

```jsx
const paginatedListings = useMemo(() => {
  const start = historyPage * historyPageSize;
  return filteredUploadListings.slice(start, start + historyPageSize);
}, [filteredUploadListings, historyPage, historyPageSize]);

const totalHistoryPages = Math.max(
  1,
  Math.ceil(filteredUploadListings.length / historyPageSize),
);
```

- [ ] **Step 2: Reset page to 0 when filters change**

Find the `useEffect` for `activeTab === "upload"` (around line 1543). Add a new `useEffect` after it:

```jsx
useEffect(() => {
  setHistoryPage(0);
}, [uploadListingsSearch, uploadListingsDateFrom, uploadListingsDateTo, uploadListingsShowIncomplete]);
```

- [ ] **Step 3: Fetch quantities when page or page size changes**

Add another `useEffect`:

```jsx
useEffect(() => {
  if (paginatedListings.length > 0) {
    fetchQuantitiesForPage(paginatedListings);
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [historyPage, historyPageSize]);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add pagination state and filter-reset logic"
```

---

## Task 4: Refresh button in `UploadListingsToolbar`

**Files:**
- Modify: `frontend/src/components/UploadListingsToolbar.jsx`

- [ ] **Step 1: Add `onRefresh` and `isRefreshing` props and refresh button**

Replace the entire file content with the updated version below. The only changes are: adding `onRefresh`/`isRefreshing` props and inserting the refresh button between the search bar and filter button.

```jsx
import { useEffect, useRef, useState } from "react";
import { Search, Filter } from "@mynaui/icons-react";
import { RefreshCw } from "lucide-react";

export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  onRefresh,
  isRefreshing,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef(null);

  const filtersActive =
    showIncompleteListings || Boolean(dateFrom?.trim()) || Boolean(dateTo?.trim());

  useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const clearDates = () => {
    onDateFromChange("");
    onDateToChange("");
  };

  return (
    <div className="mb-5 mt-8 flex flex-col gap-3 md:flex-row md:items-start md:justify-between md:gap-4">
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-border-default bg-surface-panel px-3 py-2.5 shadow-sm transition-colors focus-within:border-border-default focus-within:ring-1 focus-within:ring-border-default/40">
        <Search size={20} className="shrink-0 text-text-muted" aria-hidden />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by title…"
          className="min-w-0 flex-1 border-0 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
          aria-label="Search history by title"
        />
      </div>

      <div className="flex shrink-0 items-center gap-2 self-end md:self-start">
        {onRefresh && (
          <button
            type="button"
            aria-label="Refresh quantities"
            title="Refresh quantities"
            disabled={isRefreshing}
            onClick={onRefresh}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:border-border-default hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40 disabled:opacity-50"
          >
            <RefreshCw
              size={18}
              aria-hidden
              className={isRefreshing ? "animate-spin" : ""}
            />
          </button>
        )}

        <div className="relative" ref={rootRef}>
          <button
            type="button"
            aria-expanded={menuOpen}
            aria-haspopup="menu"
            aria-label="Open filters"
            onClick={() => setMenuOpen((o) => !o)}
            className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:border-border-default hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40"
          >
            <Filter size={20} aria-hidden />
            {filtersActive ? (
              <span
                className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-text-primary"
                aria-hidden
              />
            ) : null}
          </button>

          {menuOpen ? (
            <div
              role="menu"
              aria-label="Listing filters"
              className="absolute right-0 top-full z-30 mt-2 w-[min(calc(100vw-2rem),17rem)] origin-top-right rounded-xl border border-border-default bg-surface-panel py-3 shadow-[0_8px_30px_rgb(0,0,0,0.2)] ring-1 ring-border-default/40"
            >
              <div className="px-4 pb-2">
                <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-text-muted">
                  Visibility
                </p>
                <label className="mt-2 flex cursor-pointer items-center gap-3 text-sm text-text-primary">
                  <input
                    type="checkbox"
                    checked={showIncompleteListings}
                    onChange={(e) =>
                      onShowIncompleteListingsChange(e.target.checked)
                    }
                    className="h-3.5 w-3.5 rounded border-border-default text-text-primary focus:ring-border-default"
                  />
                  <span className="leading-snug">Show incomplete history</span>
                </label>
              </div>

              <div className="my-2 h-px bg-border-default" />

              <div className="px-4 pt-1">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-text-muted">
                    Created
                  </p>
                  {(dateFrom || dateTo) && (
                    <button
                      type="button"
                      onClick={clearDates}
                      className="text-xs font-medium text-text-muted underline-offset-2 hover:text-text-primary hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2.5">
                  <label className="block">
                    <span className="mb-1 block text-xs text-text-muted">From</span>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => onDateFromChange(e.target.value)}
                      className="w-full rounded-md border border-border-default bg-surface-muted px-2.5 py-1.5 text-sm text-text-primary transition-colors focus:border-border-default focus:bg-surface-panel focus:outline-none focus:ring-1 focus:ring-border-default/40"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs text-text-muted">To</span>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => onDateToChange(e.target.value)}
                      className="w-full rounded-md border border-border-default bg-surface-muted px-2.5 py-1.5 text-sm text-text-primary transition-colors focus:border-border-default focus:bg-surface-panel focus:outline-none focus:ring-1 focus:ring-border-default/40"
                    />
                  </label>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/UploadListingsToolbar.jsx
git commit -m "feat: add refresh button to UploadListingsToolbar"
```

---

## Task 5: Wire refresh button + pagination UI in `App.jsx`

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Pass refresh props to `UploadListingsToolbar`**

Find the `<UploadListingsToolbar` usage (around line 2270). Replace it with:

```jsx
<UploadListingsToolbar
  searchQuery={uploadListingsSearch}
  onSearchChange={setUploadListingsSearch}
  showIncompleteListings={uploadListingsShowIncomplete}
  onShowIncompleteListingsChange={setUploadListingsShowIncomplete}
  dateFrom={uploadListingsDateFrom}
  dateTo={uploadListingsDateTo}
  onDateFromChange={setUploadListingsDateFrom}
  onDateToChange={setUploadListingsDateTo}
  onRefresh={() => fetchQuantitiesForPage(paginatedListings)}
  isRefreshing={loadingQuantities}
/>
```

- [ ] **Step 2: Replace the flat list render with paginated list + pagination controls**

Find this block (around line 2299–2311):

```jsx
              ) : (
                <div className="flex flex-col gap-4">
                  {filteredUploadListings.map((listing) => (
                    <GeneratedListingCard
                      key={listing.sku}
                      listing={listing}
                      onCardClick={handleListingClick}
                      onUpload={(l) => handleUploadToEbay(l.sku, l)}
                      isUploading={uploadingSkus.has(listing.sku)}
                      uploadResult={uploadResults[listing.sku]}
                    />
                  ))}
                </div>
              )}
```

Replace it with:

```jsx
              ) : (
                <>
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
                      />
                    ))}
                  </div>

                  {/* Pagination controls */}
                  <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        aria-label="Previous page"
                        disabled={historyPage === 0}
                        onClick={() => setHistoryPage((p) => p - 1)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        ‹
                      </button>
                      <span className="min-w-[7rem] text-center text-sm text-text-muted">
                        Page {historyPage + 1} of {totalHistoryPages}
                      </span>
                      <button
                        type="button"
                        aria-label="Next page"
                        disabled={historyPage >= totalHistoryPages - 1}
                        onClick={() => setHistoryPage((p) => p + 1)}
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        ›
                      </button>
                    </div>

                    <div className="flex items-center gap-2 text-sm text-text-muted">
                      <span>Per page:</span>
                      <select
                        value={historyPageSize}
                        onChange={(e) => {
                          setHistoryPageSize(Number(e.target.value));
                          setHistoryPage(0);
                        }}
                        className="rounded-md border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-border-default/40"
                      >
                        <option value={10}>10</option>
                        <option value={25}>25</option>
                        <option value={50}>50</option>
                      </select>
                    </div>
                  </div>
                </>
              )}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: wire pagination controls and refresh button in History tab"
```

---

## Task 6: Display quantity in `GeneratedListingCard`

**Files:**
- Modify: `frontend/src/components/GeneratedListingCard.jsx`

- [ ] **Step 1: Add `quantity` prop and render it in the metadata row**

In the component signature (line 96), add `quantity` to the destructured props:

```jsx
export default function GeneratedListingCard({
  listing,
  onCardClick,
  onUpload,
  isUploading,
  uploadResult,
  quantity,
}) {
```

Then find the metadata pill row — the `<p>` with `className="mt-1 flex flex-wrap..."` (around line 246). After the closing `</span>` of the `Cat ${categoryShort}` pill and its preceding `·` separator, add a quantity pill. Insert this snippet right before the `{listing.models && (` block:

```jsx
              {quantity != null ? (
                <>
                  <span className="text-text-muted">·</span>
                  <span
                    className="whitespace-nowrap"
                    title="Live eBay stock quantity"
                  >
                    Qty: {quantity}
                  </span>
                </>
              ) : quantity === null && String(listing.ebayListingId ?? "").trim() ? (
                <>
                  <span className="text-text-muted">·</span>
                  <span className="whitespace-nowrap text-text-muted" title="Quantity unavailable">
                    Qty: —
                  </span>
                </>
              ) : null}
```

Note: `quantity` is `undefined` when the fetch hasn't returned yet (show nothing), `null` when the API explicitly returned null (show `—`), or a number (show it).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/GeneratedListingCard.jsx
git commit -m "feat: display live quantity in GeneratedListingCard metadata row"
```

---

## Task 7: Verify end-to-end

- [ ] **Step 1: Start the full dev stack**

```bash
npm run dev
```

Open `http://localhost:4000` in the browser.

- [ ] **Step 2: Check History tab loads correctly**

- Navigate to the History tab.
- Confirm only 10 cards are visible.
- Confirm the pagination bar shows "Page 1 of N" with left (disabled) and right arrows plus a per-page dropdown.

- [ ] **Step 3: Check quantity display**

- For any card whose listing is published to eBay (has the "View on eBay" button), confirm "Qty: N" or "Qty: —" appears in the metadata pill row after the category.
- For unpublished drafts, confirm no Qty pill appears.

- [ ] **Step 4: Check pagination**

- Click the right arrow — page advances to 2, new 10 cards load, quantities fetch.
- Change per-page to 25 — list updates, page resets to 1.
- Type a search term — results filter and page resets to 1.

- [ ] **Step 5: Check refresh button**

- Click the refresh icon (top-right of toolbar) — the icon spins briefly while quantities re-fetch, then stops.
- Reload the page (`Ctrl+R`) — quantities fetch automatically on load without clicking refresh.
- Switch away to another tab and back — quantities do NOT re-fetch (only the listing list refreshes).
