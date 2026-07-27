# Variant-Aware Restock for MANUAL_ Listings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make auto-restock correctly update quantity on every variation within a multi-variation MANUAL_ listing, instead of only setting the parent-level quantity (which eBay ignores for variant listings).

**Architecture:** Before issuing `ReviseInventoryStatus`, call `GetItem` (Trading API) to detect whether the listing has variations. If it does, extract each variation's SKU and build one `<InventoryStatus>` element per variation (with `<SKU>` + `<ItemID>` + `<Quantity>`), batched at 4 per API call. Non-variant listings continue unchanged.

**Tech Stack:** Python, eBay Trading API (GetItem, ReviseInventoryStatus), xml.etree.ElementTree

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/ebay_cli.py` | Modify | Add `_get_item_variation_skus()` helper; refactor `revise_inventory_status_batch()` to expand variants |

---

### Task 1: Add `_get_item_variation_skus()` helper

**Files:**
- Modify: `backend/ebay_cli.py` (insert before `revise_inventory_status_batch` at line 1659)

- [ ] **Step 1: Add the helper function**

Insert this function directly above `revise_inventory_status_batch` (before line 1659):

```python
def _get_item_variation_skus(item_id, token):
    """
    Call GetItem (Trading API) to retrieve variation SKUs for a listing.
    Returns a list of SKU strings if the listing has variations, or an empty
    list if it's a single-quantity (non-variant) listing.
    """
    headers = {
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-CALL-NAME": "GetItem",
        "X-EBAY-API-DEV-NAME": CLIENT_ID,
        "X-EBAY-API-APP-NAME": API_KEY,
        "X-EBAY-API-CERT-NAME": CLIENT_SECRET,
        "Content-Type": "text/xml",
    }
    xml_body = f"""<?xml version="1.0" encoding="utf-8"?>
<GetItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials><eBayAuthToken>{token}</eBayAuthToken></RequesterCredentials>
  <ItemID>{escape(str(item_id))}</ItemID>
  <DetailLevel>ReturnAll</DetailLevel>
</GetItemRequest>"""
    try:
        r = requests.post(
            "https://api.ebay.com/ws/api.dll",
            data=xml_body.encode("utf-8"),
            headers=headers,
            timeout=30,
        )
        if r.status_code != 200:
            return []
        ns = "{urn:ebay:apis:eBLBaseComponents}"
        root = ET.fromstring(r.text)
        if root.findtext(f"{ns}Ack", "") == "Failure":
            return []
        variations_el = root.find(f"{ns}Item/{ns}Variations")
        if variations_el is None:
            return []
        skus = []
        for var_el in variations_el.findall(f"{ns}Variation"):
            sku = var_el.findtext(f"{ns}SKU", "").strip()
            if sku:
                skus.append(sku)
        return skus
    except Exception:
        return []
```

- [ ] **Step 2: Verify no syntax errors**

Run:
```bash
python -c "from backend.ebay_cli import _get_item_variation_skus; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/ebay_cli.py
git commit -m "feat: add _get_item_variation_skus helper for Trading API variant detection"
```

---

### Task 2: Refactor `revise_inventory_status_batch()` to expand variants

**Files:**
- Modify: `backend/ebay_cli.py:1659-1724` (the `revise_inventory_status_batch` function)

- [ ] **Step 1: Replace the function with the variant-aware version**

Replace the entire `revise_inventory_status_batch` function (lines 1659-1724, accounting for the new helper above shifting line numbers) with:

```python
def revise_inventory_status_batch(items):
    """
    Update quantity for eBay listings using ReviseInventoryStatus (Trading API).
    Use this for MANUAL_ listings that don't exist in the Sell Inventory API.
    items: list of {'item_id': str, 'quantity': int} — eBay item IDs (not SKUs).
    eBay allows a maximum of 4 InventoryStatus elements per request.

    For multi-variation listings, detects variants via GetItem and sets quantity
    on each variation individually using the variation's SKU.

    Returns list of {'item_id': str, 'ok': bool}.
    """
    load_dotenv(override=True)
    token = os.getenv('user_token', '').strip()
    if not token:
        raise RuntimeError("ReviseInventoryStatus: no user_token available")
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

    # Expand items: detect variants and build per-variation InventoryStatus entries.
    # Each entry is {'item_id': str, 'quantity': int, 'sku': str|None}.
    # 'sku' is None for non-variant listings, a variation SKU string for variants.
    expanded = []
    # Track which original item_ids are variant listings so we can aggregate results
    variant_item_ids = set()
    for it in items:
        variation_skus = _get_item_variation_skus(it['item_id'], token)
        if variation_skus:
            variant_item_ids.add(it['item_id'])
            for sku in variation_skus:
                expanded.append({
                    'item_id': it['item_id'],
                    'quantity': it['quantity'],
                    'sku': sku,
                })
        else:
            expanded.append({
                'item_id': it['item_id'],
                'quantity': it['quantity'],
                'sku': None,
            })

    # Send ReviseInventoryStatus in batches of 4
    per_entry_results = []  # list of (item_id, ok)
    for i in range(0, len(expanded), 4):
        batch = expanded[i : i + 4]
        status_xml = ""
        for entry in batch:
            if entry['sku']:
                status_xml += (
                    f"<InventoryStatus>"
                    f"<ItemID>{escape(str(entry['item_id']))}</ItemID>"
                    f"<SKU>{escape(entry['sku'])}</SKU>"
                    f"<Quantity>{int(entry['quantity'])}</Quantity>"
                    f"</InventoryStatus>"
                )
            else:
                status_xml += (
                    f"<InventoryStatus>"
                    f"<ItemID>{escape(str(entry['item_id']))}</ItemID>"
                    f"<Quantity>{int(entry['quantity'])}</Quantity>"
                    f"</InventoryStatus>"
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
        if r.status_code != 200:
            for entry in batch:
                per_entry_results.append((entry['item_id'], False))
            continue
        root = ET.fromstring(r.text)
        ack = root.findtext(f"{ns}Ack", "")
        if ack == "Failure":
            for entry in batch:
                per_entry_results.append((entry['item_id'], False))
            continue
        # Parse per-entry results from response InventoryStatus elements
        responded_skus = set()
        responded_ids = set()
        for status_el in root.findall(f"{ns}InventoryStatus"):
            resp_item_id = status_el.findtext(f"{ns}ItemID", "")
            resp_sku = status_el.findtext(f"{ns}SKU", "")
            has_errors = len(status_el.findall(f"{ns}Errors")) > 0
            per_entry_results.append((resp_item_id, not has_errors))
            if resp_sku:
                responded_skus.add((resp_item_id, resp_sku))
            responded_ids.add(resp_item_id)
        # Entries not in response are treated as success (eBay omits on Warning/Success)
        for entry in batch:
            if entry['sku']:
                if (entry['item_id'], entry['sku']) not in responded_skus:
                    per_entry_results.append((entry['item_id'], True))
            else:
                if entry['item_id'] not in responded_ids:
                    per_entry_results.append((entry['item_id'], True))

    # Aggregate: for variant listings, all variations must succeed for the item to be ok.
    # For non-variant listings, there's exactly one entry so we use its result directly.
    results = []
    for it in items:
        item_id = it['item_id']
        entry_results = [ok for (eid, ok) in per_entry_results if eid == item_id]
        all_ok = all(entry_results) if entry_results else False
        results.append({"item_id": item_id, "ok": all_ok})

    return results
```

- [ ] **Step 2: Verify no syntax/import errors**

Run:
```bash
python -c "from backend.ebay_cli import revise_inventory_status_batch; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/ebay_cli.py
git commit -m "feat: expand revise_inventory_status_batch to restock all variants individually"
```

---

## Verification Checklist

- [ ] `python -c "from backend.ebay_cli import _get_item_variation_skus, revise_inventory_status_batch; print('ok')"` - no import errors
- [ ] Start backend with `npm run dev:backend`, navigate to History tab, trigger restock on a known multi-variation MANUAL_ listing and confirm all variations get updated quantity on eBay
- [ ] Confirm non-variant MANUAL_ listings still restock correctly (no regression)
- [ ] Confirm automated (non-MANUAL_) SKUs are unaffected (they don't go through this path)
