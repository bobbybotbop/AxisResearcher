# Manual Listing Import

**Date:** 2026-07-26
**Status:** Approved

## Problem

Listings created directly on ebay.com have no local representation in AxisResearcher. They are invisible in the History tab, cannot be auto-restocked, and must be managed entirely outside the tool. The goal is to automatically discover these listings at startup, store them locally alongside automated listings, and wire them into the existing History tab and auto-restock features.

## Approach

Store imported listings as `Generated_Listings/MANUAL_<ebayItemId>.json` files using the same JSON shape as automated listings. This makes them visible to all existing code that scans `Generated_Listings/*.json` with no structural changes - the only new wiring is a `isManualListing: true` flag that drives display differentiation and the restock API branch.

## Data Storage

### File naming and location

`Generated_Listings/MANUAL_<ebayItemId>.json` - one file per imported listing. The `MANUAL_` prefix guarantees no collision with automated SKUs (which use `AXIS_N` or `A_N` patterns).

### File schema

```json
{
  "sku": "MANUAL_123456789012",
  "ebayListingId": "123456789012",
  "createdDateTime": "<ListingDetails.StartTime from eBay>",
  "isManualListing": true,
  "inventoryItem": {
    "product": {
      "title": "<Title>",
      "imageUrls": ["<PictureDetails.PictureURL>"],
      "description": "<Description>"
    },
    "condition": "<ConditionDisplayName>",
    "availability": {
      "shipToLocationAvailability": { "quantity": "<Quantity>" }
    }
  },
  "offer": {
    "pricingSummary": { "price": { "value": "<BuyItNowPrice>", "currency": "USD" } },
    "quantity": "<Quantity>"
  }
}
```

### Idempotency

On each sync run, existing `MANUAL_*.json` files are never deleted. A file is only overwritten if the eBay response shows a quantity change relative to what is stored locally. Title and images are left as-is after first import to avoid unnecessary disk writes and to preserve any local edits.

### Last-refreshed timestamp

`listingPreferences.json` gets one new field: `"manual_listings_last_refreshed": "<ISO datetime>"`. This is written after every successful sync. On the next run, `ModTimeFrom` in the GetSellerList request is set to this value so only listings modified since the last sync are re-fetched. A null or missing value triggers a full fetch (first run).

## eBay API: GetSellerList

### Why GetSellerList (Trading API)

The Sell Inventory API only lists items that were created via the Inventory API and have a SKU. Listings created on ebay.com don't exist there. GetSellerList (Trading API XML/SOAP) returns all active listings by eBay item ID regardless of origin - the same auth path already used for `add_item` in `ebay_cli.py`.

### Request shape

```xml
<GetSellerListRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{user_token}</eBayAuthToken>
  </RequesterCredentials>
  <ActiveList>true</ActiveList>
  <Pagination>
    <EntriesPerPage>200</EntriesPerPage>
    <PageNumber>{page}</PageNumber>
  </Pagination>
  <!-- Only on incremental runs (last_refreshed is set): -->
  <ModTimeFrom>{last_refreshed_iso}</ModTimeFrom>
  <!-- Always: -->
  <DetailLevel>ReturnAll</DetailLevel>
  <OutputSelector>ItemID,Title,PictureDetails,Quantity,BuyItNowPrice,
    ConditionDisplayName,ListingDetails,Description</OutputSelector>
</GetSellerListRequest>
```

Pagination: loop until `HasMoreItems` is false or `PageNumber > TotalNumberOfPages`.

### Filtering imported vs. automated

After fetching, exclude any listing whose `ItemID` matches an `ebayListingId` already present in a non-MANUAL `Generated_Listings/*.json` file. This prevents re-importing listings that were originally created by this tool. Only the remaining items are written as `MANUAL_*.json`.

## Backend: New Endpoints

### `POST /api/import-listings`

Triggers a full or incremental GetSellerList sync.

1. Load `manual_listings_last_refreshed` from `listingPreferences.json`.
2. Call GetSellerList with pagination, applying `ModTimeFrom` if available.
3. Load all existing non-MANUAL `Generated_Listings/*.json` to collect known `ebayListingId` values.
4. For each returned item not in the known set, write `Generated_Listings/MANUAL_<itemId>.json` (creating or updating quantity only if changed).
5. Update `manual_listings_last_refreshed` in `listingPreferences.json`.
6. Return `{ "imported": N, "updated": M, "skipped": K }`.

### `DELETE /api/imported-listings/<sku>` (optional, for future)

Not in scope for this implementation but the `MANUAL_` prefix makes this trivially safe to add later.

No changes needed to `GET /api/listings` - it already scans all `Generated_Listings/*.json` files and will pick up `MANUAL_*` files automatically. The `isManualListing` field is surfaced as-is in the listing summaries.

## Backend: Auto-Restock Branch

`POST /api/listings/restock` currently uses:
1. `GET /sell/inventory/v1/offer?sku={sku}` to get the offer ID
2. `POST /sell/inventory/v1/bulk_update_price_quantity` to set quantity

For `MANUAL_*` SKUs, step 1 will fail (no offer in the Inventory API). The fix: before the Inventory API path, detect MANUAL SKUs and route them through Trading API `ReviseInventoryStatus`:

```xml
<ReviseInventoryStatusRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{user_token}</eBayAuthToken>
  </RequesterCredentials>
  <InventoryStatus>
    <ItemID>{ebayListingId}</ItemID>
    <Quantity>{targetQty}</Quantity>
  </InventoryStatus>
  ...up to 4 items per request...
</ReviseInventoryStatusRequest>
```

`ReviseInventoryStatus` accepts up to 4 items per call; batch accordingly (vs. 25 for `bulk_update_price_quantity`). After a successful restock, call `update_local_listing_quantity(sku, quantity)` from `combine_data.py` exactly as the existing path does.

The split: build two lists from the restock request's SKU list - `manual_skus` (prefix `MANUAL_`) and `automated_skus` (everything else). Run both paths and merge results.

## Frontend: Startup + Manual Refresh

### Startup trigger

In `App.jsx`'s mount-time `useEffect` (the single `useEffect(fn, [])` at line 619), call `importListingsFromEbay()` after `handleRefreshTokens()`. This runs once per session open.

```js
hasAutoRefreshed.current = true;
await handleRefreshTokens();   // ensure user token is fresh before import
importListingsFromEbay();      // new - runs in background, does not block UI
```

`importListingsFromEbay()` calls `POST /api/import-listings` in the background (no blocking UI). Errors are swallowed silently - a failed import is non-fatal. Awaiting `handleRefreshTokens` first avoids a race where import fires with a stale/expired user token.

### Manual refresh button

The History tab's existing toolbar has an `onRefresh` / `isRefreshing` prop pair. Wire this button to call `POST /api/import-listings` followed by `fetchAllListings()` so the list refreshes with any newly imported items. Show a spinner on the button while in-flight.

## Frontend: History Tab Display

### Manual listing border

In the listing row component, detect `listing.isManualListing === true` and apply a thicker border using the same border color token already in use (`border-border-default`). Automated listings use the default `border` width; manual listings use `border-2` (or `border-[3px]` if 2px is not visually distinct enough).

No color change - same token, heavier weight.

### Filter toggle

Add a "Show manual listings" checkbox to the Visibility section of `UploadListingsToolbar`'s filter dropdown. Default: **on** (manual listings visible by default). When unchecked, `filteredUploadListings` filters out rows where `listing.isManualListing === true`.

New props on `UploadListingsToolbar`:
- `showManualListings: bool` (default `true`)
- `onShowManualListingsChange: (bool) => void`

New state in `App.jsx`:
```js
const [uploadListingsShowManual, setUploadListingsShowManual] = useState(true);
```

The `filtersActive` dot indicator on the filter button activates when `showManualListings === false` (same as the other visibility toggles).

## Files to Modify

| File | Change |
|------|--------|
| `app.py` | Add `POST /api/import-listings` endpoint; branch `POST /api/listings/restock` for `MANUAL_` SKUs using `ReviseInventoryStatus`; surface `isManualListing` in `GET /api/listings` listing summaries |
| `backend/ebay_cli.py` or `app.py` | Add `get_seller_list(mod_time_from=None)` function wrapping GetSellerList with pagination |
| `backend/copyScripts/combine_data.py` | Add `manual_listings_last_refreshed` read/write helpers (alongside existing `get_auto_restock_settings`) |
| `listingPreferences.json` | Add `manual_listings_last_refreshed` field (written at runtime, not hard-coded) |
| `frontend/src/App.jsx` | Add `importListingsFromEbay()`, call it on mount; add `uploadListingsShowManual` state; pass new props to toolbar and filter memo |
| `frontend/src/components/UploadListingsToolbar.jsx` | Add "Show manual listings" checkbox to Visibility section; include in `filtersActive` |
| Listing row component (wherever rows are rendered in App.jsx) | Apply `border-2` (or equivalent) to rows where `listing.isManualListing === true` |

## Verification

1. **First run:** Open the app with a real eBay user token. `POST /api/import-listings` fires on startup. Check that `Generated_Listings/MANUAL_*.json` files appear for each of your manually-created eBay listings.
2. **Incremental sync:** Note the `manual_listings_last_refreshed` timestamp in `listingPreferences.json`. Open the app again. Verify no duplicate files are created and the timestamp updates.
3. **History tab display:** Navigate to History. Manual listing rows should have a visibly thicker border. Toggle "Show manual listings" off - those rows disappear. Toggle on - they return.
4. **Filter dot:** When "Show manual listings" is unchecked, the filter dot should appear on the funnel button.
5. **Auto-restock:** Enable auto-restock. Navigate to the History tab. Verify that `MANUAL_*` listings get their quantity updated via `ReviseInventoryStatus` (check network traffic or eBay seller hub for the updated quantity).
6. **Manual refresh:** Click the Refresh button in the History tab toolbar. Verify it re-runs the import and re-fetches the listing list.
7. **No collision:** Confirm that listings originally created by this tool (with a real `ebayListingId` in a non-MANUAL file) do not appear as duplicate `MANUAL_*` files.
