# Manual Listing Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-import active eBay listings created outside this tool into `Generated_Listings/MANUAL_<itemId>.json` files so they appear in the History tab, participate in auto-restock, and are visually distinguished by a thicker border.

**Architecture:** Each imported listing gets a `Generated_Listings/MANUAL_<ebayItemId>.json` file using the same JSON shape as automated listings. The `isManualListing: true` flag drives display differentiation and routes restocking through Trading API `ReviseInventoryStatus` instead of the Sell Inventory API. Sync runs on startup (after token refresh) and on manual History tab refresh, using `ModTimeFrom` for incremental fetches after the first run.

**Tech Stack:** Python/Flask backend, React/Vite frontend, eBay Trading API (GetSellerList, ReviseInventoryStatus), existing `listingPreferences.json` for persisting the last-sync timestamp.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/ebay_cli.py` | Modify | Add `get_seller_list()` and `revise_inventory_status_batch()` |
| `backend/copyScripts/combine_data.py` | Modify | Add timestamp getters/setters and `write_manual_listing_json()` |
| `app.py` | Modify | Add `POST /api/import-listings`; branch `/api/listings/quantities` and `/api/listings/restock` for MANUAL_ SKUs; surface `isManualListing` in `/api/listings` |
| `frontend/src/App.jsx` | Modify | Add `importListingsFromEbay()`, startup call, manual refresh wiring, `uploadListingsShowManual` state, filter memo update |
| `frontend/src/components/UploadListingsToolbar.jsx` | Modify | Add "Show manual listings" checkbox |
| `frontend/src/components/GeneratedListingCard.jsx` | Modify | Accept `isManual` prop; apply thick border |
| `frontend/src/components/CompactListingRow.jsx` | Modify | Accept `isManual` prop; apply thick border |

---

### Task 1: `get_seller_list()` in `backend/ebay_cli.py`

**Files:**
- Modify: `backend/ebay_cli.py` (append after `add_item`)

`get_seller_list` uses the same Trading API XML/header pattern as `add_item`. The constants `CLIENT_ID`, `API_KEY`, `CLIENT_SECRET` are already declared at module scope in `ebay_cli.py` — use them directly. `helper_get_valid_token()` is already defined in the same file.

- [ ] **Step 1: Add `get_seller_list()` to `backend/ebay_cli.py`**

Append after the closing of the `add_item` function:

```python
def get_seller_list(mod_time_from=None):
    """
    Fetch all active fixed-price listings for the authenticated seller via GetSellerList.
    mod_time_from: ISO datetime string (e.g. "2026-07-01T00:00:00+00:00"). When provided,
                   only listings modified since that time are returned.
    Returns list of dicts: {item_id, title, quantity, price, image_urls, condition,
                            start_time, description}.
    """
    token = helper_get_valid_token()
    ns = '{urn:ebay:apis:eBLBaseComponents}'
    headers = {
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "GetSellerList",
        "X-EBAY-API-DEV-NAME": CLIENT_ID,
        "X-EBAY-API-APP-NAME": API_KEY,
        "X-EBAY-API-CERT-NAME": CLIENT_SECRET,
        "Content-Type": "text/xml",
    }
    items = []
    page = 1
    while True:
        mod_xml = f'<ModTimeFrom>{mod_time_from}</ModTimeFrom>' if mod_time_from else ''
        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetSellerListRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <GranularityLevel>Fine</GranularityLevel>
  {mod_xml}
  <Pagination>
    <EntriesPerPage>200</EntriesPerPage>
    <PageNumber>{page}</PageNumber>
  </Pagination>
</GetSellerListRequest>"""
        r = requests.post(
            "https://api.ebay.com/ws/api.dll",
            data=xml_body.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
        root = ET.fromstring(r.text)
        ack = root.findtext(f"{ns}Ack", "")
        if ack not in ("Success", "Warning"):
            errors = root.findall(f"{ns}Errors")
            msg = "; ".join(
                e.findtext(f"{ns}ShortMessage", "") for e in errors
            )
            raise RuntimeError(f"GetSellerList failed (Ack={ack}): {msg}")
        item_array = root.find(f"{ns}ItemArray")
        if item_array is None:
            break
        for item_el in item_array.findall(f"{ns}Item"):
            pictures = [
                p.text
                for p in item_el.findall(f"{ns}PictureDetails/{ns}PictureURL")
                if p.text
            ]
            price_el = item_el.find(f"{ns}BuyItNowPrice")
            if price_el is None:
                price_el = item_el.find(f"{ns}SellingStatus/{ns}CurrentPrice")
            items.append({
                "item_id": item_el.findtext(f"{ns}ItemID", ""),
                "title": item_el.findtext(f"{ns}Title", ""),
                "quantity": int(item_el.findtext(f"{ns}Quantity", "0") or 0),
                "price": price_el.text if price_el is not None else "0.00",
                "image_urls": pictures,
                "condition": item_el.findtext(f"{ns}ConditionDisplayName", ""),
                "start_time": item_el.findtext(f"{ns}ListingDetails/{ns}StartTime", ""),
                "description": item_el.findtext(f"{ns}Description", ""),
            })
        has_more = root.findtext(f"{ns}HasMoreItems", "false").lower()
        if has_more != "true":
            break
        page += 1
    return items
```

- [ ] **Step 2: Smoke-test manually**

Open a Python shell at the project root and run:
```python
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from backend.ebay_cli import get_seller_list
items = get_seller_list()
print(len(items), 'listings found')
if items: print(items[0])
```
Expected: a list of dicts with `item_id`, `title`, etc. No exception.

- [ ] **Step 3: Commit**

```bash
git add backend/ebay_cli.py
git commit -m "feat: add get_seller_list() via Trading API GetSellerList"
```

---

### Task 2: `revise_inventory_status_batch()` in `backend/ebay_cli.py`

**Files:**
- Modify: `backend/ebay_cli.py` (append after `get_seller_list`)

- [ ] **Step 1: Add `revise_inventory_status_batch()` to `backend/ebay_cli.py`**

```python
def revise_inventory_status_batch(items):
    """
    Update quantity for eBay listings using ReviseInventoryStatus (Trading API).
    Use this for MANUAL_ listings that don't exist in the Sell Inventory API.
    items: list of {'item_id': str, 'quantity': int} — eBay item IDs (not SKUs).
    eBay allows a maximum of 4 InventoryStatus elements per request.
    Returns list of {'item_id': str, 'ok': bool}.
    """
    token = helper_get_valid_token()
    ns = "{urn:ebay:apis:eBLBaseComponents}"
    headers = {
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "ReviseInventoryStatus",
        "X-EBAY-API-DEV-NAME": CLIENT_ID,
        "X-EBAY-API-APP-NAME": API_KEY,
        "X-EBAY-API-CERT-NAME": CLIENT_SECRET,
        "Content-Type": "text/xml",
    }
    results = []
    for i in range(0, len(items), 4):
        batch = items[i : i + 4]
        status_xml = "".join(
            f"<InventoryStatus>"
            f"<ItemID>{it['item_id']}</ItemID>"
            f"<Quantity>{it['quantity']}</Quantity>"
            f"</InventoryStatus>"
            for it in batch
        )
        xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<ReviseInventoryStatusRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  {status_xml}
</ReviseInventoryStatusRequest>"""
        r = requests.post(
            "https://api.ebay.com/ws/api.dll",
            data=xml_body.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
        root = ET.fromstring(r.text)
        ack = root.findtext(f"{ns}Ack", "")
        ok = ack in ("Success", "Warning")
        for it in batch:
            results.append({"item_id": it["item_id"], "ok": ok})
    return results
```

- [ ] **Step 2: Commit**

```bash
git add backend/ebay_cli.py
git commit -m "feat: add revise_inventory_status_batch() via Trading API"
```

---

### Task 3: Config helpers + `write_manual_listing_json()` in `combine_data.py`

**Files:**
- Modify: `backend/copyScripts/combine_data.py` (append to bottom of file)

`load_config()` and `save_config()` are already in this file. The new helpers follow the same pattern as `get_auto_restock_settings()` / `save_auto_restock_settings()`.

- [ ] **Step 1: Add timestamp helpers and write helper to `combine_data.py`**

Append to the bottom of `backend/copyScripts/combine_data.py`:

```python
def get_manual_import_last_refreshed():
    """Returns the last manual import timestamp as ISO string, or None if never run."""
    config = load_config()
    return config.get("manual_listings_last_refreshed")


def save_manual_import_last_refreshed(dt_str):
    """Persists the manual import timestamp to listingPreferences.json."""
    config = load_config()
    config["manual_listings_last_refreshed"] = dt_str
    save_config(config)


def write_manual_listing_json(item):
    """
    Write (or update) Generated_Listings/MANUAL_<itemId>.json from a get_seller_list() item.
    item keys: item_id, title, quantity, price, image_urls, condition, start_time, description.
    Only overwrites an existing file when quantity has changed (to avoid churn).
    Returns True if the file was written, False if unchanged and skipped.
    """
    sku = f"MANUAL_{item['item_id']}"
    path = os.path.join("Generated_Listings", f"{sku}.json")
    os.makedirs("Generated_Listings", exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("offer", {}).get("quantity") == item["quantity"]:
                return False
        except (json.JSONDecodeError, KeyError):
            pass  # corrupt — overwrite
    data = {
        "sku": sku,
        "ebayListingId": item["item_id"],
        "createdDateTime": item["start_time"],
        "isManualListing": True,
        "inventoryItem": {
            "product": {
                "title": item["title"],
                "imageUrls": item["image_urls"],
                "description": item["description"],
            },
            "condition": item["condition"],
            "availability": {
                "shipToLocationAvailability": {"quantity": item["quantity"]}
            },
        },
        "offer": {
            "pricingSummary": {
                "price": {"value": item["price"], "currency": "USD"}
            },
            "quantity": item["quantity"],
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True
```

Note: `os` and `json` are already imported at the top of `combine_data.py`.

- [ ] **Step 2: Commit**

```bash
git add backend/copyScripts/combine_data.py
git commit -m "feat: add manual import helpers to combine_data"
```

---

### Task 4: `POST /api/import-listings` endpoint in `app.py`

**Files:**
- Modify: `app.py` (add new route near the existing `/api/listings` block around line 1490)

- [ ] **Step 1: Add the import to `app.py`'s imports block**

Find the line in `app.py` that imports from `combine_data` (search for `from backend.copyScripts.combine_data import`). Add the two new names to that import:

```python
from backend.copyScripts.combine_data import (
    # ... existing imports ...,
    get_manual_import_last_refreshed,
    save_manual_import_last_refreshed,
    write_manual_listing_json,
)
```

Also find the line importing from `ebay_cli` and add the two new functions:
```python
from backend.ebay_cli import (
    # ... existing imports ...,
    get_seller_list,
    revise_inventory_status_batch,
)
```

- [ ] **Step 2: Add `POST /api/import-listings` route**

Add this route after the closing of the `/api/listings` route (around line 1577):

```python
@app.route('/api/import-listings', methods=['POST'])
def api_import_listings():
    """
    Sync active eBay listings created outside this tool into Generated_Listings/MANUAL_*.json.
    Uses ModTimeFrom from listingPreferences.json for incremental fetches after the first run.
    """
    last_refreshed = get_manual_import_last_refreshed()
    try:
        items = get_seller_list(mod_time_from=last_refreshed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # Build set of eBay item IDs already claimed by non-MANUAL listings
    known_ids = set()
    for fpath in glob.glob('Generated_Listings/*.json'):
        if os.path.basename(fpath).startswith('MANUAL_'):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                d = json.load(f)
            eid = str(d.get('ebayListingId') or '').strip()
            if eid:
                known_ids.add(eid)
        except Exception:
            continue

    imported = updated = skipped = 0
    for item in items:
        if item['item_id'] in known_ids:
            skipped += 1
            continue
        sku = f'MANUAL_{item["item_id"]}'
        path = os.path.join('Generated_Listings', f'{sku}.json')
        is_new = not os.path.exists(path)
        written = write_manual_listing_json(item)
        if written:
            imported += 1 if is_new else 0
            updated += 0 if is_new else 1
        else:
            skipped += 1

    save_manual_import_last_refreshed(
        datetime.now(timezone.utc).isoformat()
    )
    return jsonify({'imported': imported, 'updated': updated, 'skipped': skipped})
```

Verify `glob`, `json`, `os`, `datetime`, `timezone` are already imported at the top of `app.py`. If `datetime`/`timezone` aren't, add `from datetime import datetime, timezone` near the top.

- [ ] **Step 3: Test the endpoint manually**

With `python app.py` running:
```bash
curl -X POST http://localhost:5000/api/import-listings
```
Expected response: `{"imported": N, "updated": 0, "skipped": M}` where `N` = number of manual listings found.
Check that `Generated_Listings/MANUAL_*.json` files now exist.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add POST /api/import-listings to sync manual eBay listings"
```

---

### Task 5: Surface `isManualListing` + branch `/api/listings/quantities` for MANUAL_ SKUs

**Files:**
- Modify: `app.py` (two separate changes)

**Change A:** In `list_all_listings` (the `GET /api/listings` handler, around line 1548), add `isManualListing` to the summary dict that is built from each JSON file.

**Change B:** In `api_listings_quantities` (around line 1806), skip the Inventory API for MANUAL_ SKUs and return the stored quantity from the local JSON file instead.

- [ ] **Step 1: Add `isManualListing` to `/api/listings` summary**

In `list_all_listings`, find the dict literal that builds each listing summary (it ends around line 1548). Add one key after `'models'`:

```python
'isManualListing': bool(listing_data.get('isManualListing', False)),
```

The full dict should now include this line alongside the existing fields.

- [ ] **Step 2: Branch `/api/listings/quantities` for MANUAL_ SKUs**

In `api_listings_quantities` (around line 1806), find the loop that iterates over SKUs. At the very start of the loop body (before the Inventory API call), insert:

```python
if sku.startswith('MANUAL_'):
    fpath = os.path.join('Generated_Listings', f'{sku}.json')
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            d = json.load(f)
        quantities[sku] = int(d.get('offer', {}).get('quantity', 0))
    except Exception:
        quantities[sku] = None
    continue
```

This returns the stored quantity (kept in sync by the restock path) without hitting the Inventory API.

- [ ] **Step 3: Verify `/api/listings` returns `isManualListing`**

```bash
curl http://localhost:5000/api/listings | python -m json.tool | grep -A2 isManualListing
```
Expected: MANUAL_ listings show `"isManualListing": true`; automated listings show `"isManualListing": false`.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: surface isManualListing in listings API; serve stored qty for MANUAL_ SKUs"
```

---

### Task 6: Branch `/api/listings/restock` for MANUAL_ SKUs

**Files:**
- Modify: `app.py` (`api_restock_listings`, around line 1922)

The existing restock path uses Sell Inventory API `bulk_update_price_quantity` (works for automated SKUs). MANUAL_ SKUs route through `revise_inventory_status_batch` instead.

- [ ] **Step 1: Split SKU list and add MANUAL_ path**

In `api_restock_listings`, after `skus` and `quantity` are read from the request body, replace the single-path flow with a split:

```python
# Partition incoming SKUs into manual (Trading API) vs automated (Inventory API)
manual_items = []
automated_skus = []
for sku in skus:
    if sku.startswith('MANUAL_'):
        # ebayListingId is the part after "MANUAL_"
        manual_items.append({'item_id': sku[len('MANUAL_'):], 'quantity': quantity})
    else:
        automated_skus.append(sku)
```

Then run both paths and merge results. Replace the entire body of `api_restock_listings` after the `quantity` validation block with:

```python
if not skus:
    return jsonify({'updated': [], 'failed': [], 'quantity': quantity}), 200

token = os.getenv('user_token', '').strip()
if not token:
    return jsonify({'updated': [], 'failed': skus, 'quantity': quantity,
                    'error': 'No user token available'}), 200

# Partition into manual (Trading API) vs automated (Sell Inventory API)
manual_items = []
automated_skus = []
for sku in skus:
    if sku.startswith('MANUAL_'):
        manual_items.append({'item_id': sku[len('MANUAL_'):], 'quantity': quantity})
    else:
        automated_skus.append(sku)

updated = []
failed = []

# --- MANUAL_ path: Trading API ReviseInventoryStatus ---
if manual_items:
    results = revise_inventory_status_batch(manual_items)
    for res in results:
        sku = f'MANUAL_{res["item_id"]}'
        if res['ok']:
            update_local_listing_quantity(sku=sku, quantity=quantity)
            updated.append(sku)
        else:
            failed.append(sku)

# --- Automated path: Sell Inventory API bulk_update_price_quantity ---
if automated_skus:
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    sku_offer_ids = {}
    for sku in automated_skus:
        try:
            r = requests.get(
                f'https://api.ebay.com/sell/inventory/v1/offer?sku={sku}',
                headers=headers,
                timeout=10,
            )
            if r.status_code == 200:
                offers = r.json().get('offers', [])
                if offers:
                    sku_offer_ids[sku] = offers[0].get('offerId')
        except Exception:
            pass

    batch_size = 25
    for i in range(0, len(automated_skus), batch_size):
        batch = automated_skus[i:i + batch_size]
        requests_list = []
        for sku in batch:
            entry = {
                'sku': sku,
                'shipToLocationAvailability': {'quantity': quantity},
            }
            offer_id = sku_offer_ids.get(sku)
            if offer_id:
                entry['offers'] = [
                    {'offerId': offer_id, 'availableQuantity': quantity}
                ]
            requests_list.append(entry)
        try:
            r = requests.post(
                'https://api.ebay.com/sell/inventory/v1/bulk_update_price_quantity',
                headers=headers,
                json={'requests': requests_list},
                timeout=30,
            )
            if r.status_code not in (200, 207):
                failed.extend(batch)
                continue
            data = r.json() or {}
            status_by_sku = {
                resp.get('sku'): resp.get('statusCode')
                for resp in data.get('responses', [])
            }
            for sku in batch:
                if status_by_sku.get(sku) == 200:
                    updated.append(sku)
                else:
                    failed.append(sku)
        except Exception:
            failed.extend(batch)

    for sku in [s for s in updated if not s.startswith('MANUAL_')]:
        update_local_listing_quantity(sku=sku, quantity=quantity)

return jsonify({'updated': updated, 'failed': failed, 'quantity': quantity}), 200
```

- [ ] **Step 2: Test restock with a MANUAL_ listing**

With the backend running and at least one MANUAL_ file present:
```bash
curl -X POST http://localhost:5000/api/listings/restock \
  -H "Content-Type: application/json" \
  -d '{"skus": ["MANUAL_<itemId>"], "quantity": 15}'
```
Expected: `{"updated": ["MANUAL_<itemId>"], "failed": [], "quantity": 15}`
Check the MANUAL_ JSON file — `offer.quantity` should now be 15.
Check eBay seller hub — the listing's quantity should update.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: route MANUAL_ SKU restock through ReviseInventoryStatus"
```

---

### Task 7: Frontend `importListingsFromEbay()` + startup and manual refresh wiring

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add `importListingsFromEbay` function to `App.jsx`**

Near the top of `App.jsx` (near the other `fetch`-based helpers, before the JSX return), add:

```js
const importListingsFromEbay = async () => {
  try {
    await fetch('/api/import-listings', { method: 'POST' });
  } catch {
    // non-fatal — import failure doesn't block the UI
  }
};
```

- [ ] **Step 2: Call it on startup in the mount `useEffect`**

Find the mount-time `useEffect` with `[]` dependency (around line 621). It currently ends with:

```js
hasAutoRefreshed.current = true;
handleRefreshTokens();
```

Change to:

```js
hasAutoRefreshed.current = true;
await handleRefreshTokens();
importListingsFromEbay();
```

Note: `handleRefreshTokens` must now be awaited. If it doesn't currently return a Promise, wrap its body in an async call or add `return` to its internal `fetch` chain. Verify `handleRefreshTokens` definition and ensure it returns a Promise — typically it already does if it uses `fetch(...)`.

- [ ] **Step 3: Wire manual refresh on History tab to also import**

Find where `onRefresh` is defined in App.jsx (the prop passed to `UploadListingsToolbar` for the refresh button). It currently calls only `fetchAllListings()`. Change it to:

```js
const handleHistoryRefresh = async () => {
  setIsRefreshingListings(true);
  await importListingsFromEbay();
  await fetchAllListings();
  setIsRefreshingListings(false);
};
```

Then pass `onRefresh={handleHistoryRefresh}` to `UploadListingsToolbar`. (The existing `isRefreshing` prop name and state variable may vary — match whatever is currently used.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: auto-import manual listings on startup and manual refresh"
```

---

### Task 8: Filter toggle (state, memo, toolbar checkbox)

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/UploadListingsToolbar.jsx`

- [ ] **Step 1: Add `uploadListingsShowManual` state to `App.jsx`**

Find the block of `useState` declarations for History tab filters (near `uploadListingsShowIncomplete`, `uploadListingsShowUnuploaded`). Add:

```js
const [uploadListingsShowManual, setUploadListingsShowManual] = useState(true);
```

Default `true` = manual listings visible by default.

- [ ] **Step 2: Add filter clause to `filteredUploadListings` useMemo**

In the `filteredUploadListings` useMemo (around line 732), add a new filter line after the existing unuploaded filter:

```js
if (!uploadListingsShowManual && listing.isManualListing) return false;
```

Also add `uploadListingsShowManual` to the dependency array at the bottom of the memo.

- [ ] **Step 3: Pass new props to `UploadListingsToolbar`**

Find where `UploadListingsToolbar` is rendered in the History tab JSX. Add two new props:

```jsx
showManualListings={uploadListingsShowManual}
onShowManualListingsChange={setUploadListingsShowManual}
```

- [ ] **Step 4: Add checkbox to `UploadListingsToolbar.jsx`**

In `UploadListingsToolbar.jsx`, add `showManualListings` and `onShowManualListingsChange` to the props object (alongside `showIncompleteListings`, `showUnuploadedListings`, etc.).

In the `filtersActive` calculation (around line 38), add:
```js
|| !showManualListings
```

In the JSX, under the "Visibility" section after the "Show unuploaded listings" `</label>` (around line 156), insert:

```jsx
<label className="mt-2 flex cursor-pointer items-center gap-3 text-sm text-text-primary">
  <input
    type="checkbox"
    checked={showManualListings}
    onChange={(e) => onShowManualListingsChange(e.target.checked)}
    className="h-3.5 w-3.5 rounded border-border-default text-text-primary focus:ring-border-default"
  />
  <span className="leading-snug">Show manually listed items</span>
</label>
```

- [ ] **Step 5: Verify the filter works**

In the browser on the History tab:
1. Open the filter dropdown — confirm "Show manually listed items" checkbox is present and checked.
2. Uncheck it — MANUAL_ listing rows should disappear.
3. Re-check — they return.
4. With it unchecked, confirm the red dot appears on the filter funnel button.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/UploadListingsToolbar.jsx
git commit -m "feat: add show/hide manual listings filter to History tab"
```

---

### Task 9: Bold border on manual listing rows

**Files:**
- Modify: `frontend/src/components/GeneratedListingCard.jsx`
- Modify: `frontend/src/components/CompactListingRow.jsx`
- Modify: `frontend/src/App.jsx` (pass `isManual` prop)

Both card components currently use the same outermost className:
```
flex w-full cursor-pointer flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md md:flex-row md:items-stretch
```

The goal: keep the same `border-border-default` color but use `border-2` (2px) for manual listings instead of `border` (1px).

- [ ] **Step 1: Add `isManual` prop to `GeneratedListingCard.jsx`**

Add `isManual = false` to the destructured props at the top of the component. Change the outermost `div`'s `className` from the static string to a conditional:

```jsx
className={`flex w-full cursor-pointer flex-col overflow-hidden rounded-xl ${isManual ? 'border-2' : 'border'} border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md md:flex-row md:items-stretch`}
```

- [ ] **Step 2: Add `isManual` prop to `CompactListingRow.jsx`**

Same change — add `isManual = false` to props and apply the same conditional className as above. The outermost `div` in `CompactListingRow` has the identical class string.

- [ ] **Step 3: Pass `isManual` from `App.jsx`**

In `App.jsx`, find the `paginatedListings.map(...)` block (around line 3102). Both `GeneratedListingCard` and `CompactListingRow` are rendered there. Add the prop to both:

```jsx
isManual={!!listing.isManualListing}
```

- [ ] **Step 4: Verify visually**

In the browser on the History tab, MANUAL_ listing cards should now have a noticeably thicker border compared to automated listings — same color, heavier weight.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/GeneratedListingCard.jsx \
        frontend/src/components/CompactListingRow.jsx \
        frontend/src/App.jsx
git commit -m "feat: show thicker border on manually imported listing cards"
```

---

## Verification Checklist

- [ ] `python -c "from backend.ebay_cli import get_seller_list, revise_inventory_status_batch; print('ok')"` — no import errors
- [ ] `POST /api/import-listings` creates `Generated_Listings/MANUAL_*.json` files matching active eBay listings not created by this tool
- [ ] Second run: no duplicate files, `manual_listings_last_refreshed` timestamp updated in `listingPreferences.json`
- [ ] `GET /api/listings` response includes `isManualListing: true` for MANUAL_ entries
- [ ] History tab shows MANUAL_ listings with a thicker border
- [ ] Filter dropdown has "Show manually listed items" checkbox; unchecking hides manual rows and shows the red dot
- [ ] Auto-restock (or "Restock now") successfully updates quantity on a MANUAL_ listing — verify via eBay seller hub
- [ ] Automated listings are not affected by the restock branch change
- [ ] Listings originally created by this tool (with real `ebayListingId` in a non-MANUAL file) do not get a duplicate `MANUAL_*` file
