# Promoted Listings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every successful listing upload, automatically enroll the listing in a Promoted Listings Standard (PLS) campaign on eBay at a configurable ad rate, controlled by a Settings toggle.

**Architecture:** A new `backend/promoted_listings.py` module handles all Marketing API calls in isolation. `backend/copyScripts/combine_data.py` gets new preference read/write helpers for the three new fields (`auto_promote_enabled`, `promoted_listing_ad_rate`, `promoted_listing_campaign_id`, `promoted_listing_ad_group_id`). `app.py` gains two settings endpoints and calls `promote_listing()` after a successful upload. The Settings tab gets a new "Promoted Listings" section. The `sell.marketing` OAuth scope is added to `refreshToken.py`.

**Tech Stack:** Python/Flask backend, React/Vite frontend, Tailwind v4, eBay Sell Marketing REST API v1.

---

## File Map

| File | Change |
|------|--------|
| `backend/promoted_listings.py` | **Create** — all Marketing API logic |
| `backend/copyScripts/combine_data.py` | **Modify** — add `get_promoted_listing_settings`, `save_promoted_listing_settings`, `get_promoted_listing_campaign_ids`, `save_promoted_listing_campaign_ids` |
| `backend/refreshToken.py` | **Modify** — add `sell.marketing` to `DEFAULT_USER_SCOPES` |
| `app.py` | **Modify** — add 2 settings routes, call `promote_listing` after upload, add imports |
| `frontend/src/App.jsx` | **Modify** — add Promoted Listings settings section |
| `listingPreferences.json` | **Modify** — add 4 new fields (done manually or via first settings save) |

---

## Task 1: Add `sell.marketing` scope to OAuth

**Files:**
- Modify: `backend/refreshToken.py:42-45`

- [ ] **Step 1: Add scope to DEFAULT_USER_SCOPES**

In `backend/refreshToken.py`, find `DEFAULT_USER_SCOPES` (line 42). Add the marketing scope:

```python
DEFAULT_USER_SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
    "https://api.ebay.com/oauth/api_scope/sell.marketing",
]
```

- [ ] **Step 2: Verify the change looks right**

```bash
python -c "from backend.refreshToken import DEFAULT_USER_SCOPES; print(DEFAULT_USER_SCOPES)"
```

Expected output includes `sell.marketing`.

- [ ] **Step 3: Commit**

```bash
git add backend/refreshToken.py
git commit -m "feat: add sell.marketing scope to OAuth user scopes"
```

> **Note:** After this change, the next time the user re-authenticates via `python -m backend.refreshToken open-consent`, the new token will include `sell.marketing`. Existing tokens without this scope will get a 403 from the Marketing API (handled as a non-fatal warning in Task 3).

---

## Task 2: Add preference helpers in `combine_data.py`

**Files:**
- Modify: `backend/copyScripts/combine_data.py` (append after line 503, after `save_minimum_images_setting`)

- [ ] **Step 1: Append the four new helper functions**

Open `backend/copyScripts/combine_data.py` and append after `save_minimum_images_setting`:

```python

def get_promoted_listing_settings():
    """
    Read promoted listing settings from listingPreferences.json.

    Returns:
        dict: {"auto_promote_enabled": bool, "promoted_listing_ad_rate": float}
    """
    config = load_config()
    return {
        "auto_promote_enabled": bool(config.get("auto_promote_enabled", True)),
        "promoted_listing_ad_rate": float(config.get("promoted_listing_ad_rate", 7.0)),
    }


def save_promoted_listing_settings(enabled=None, ad_rate=None):
    """
    Persist promoted listing settings to listingPreferences.json.

    Args:
        enabled (bool, optional): New enabled state. Unchanged if None.
        ad_rate (float, optional): New ad rate percent (0.1-100). Unchanged if None.

    Returns:
        dict: {"auto_promote_enabled": bool, "promoted_listing_ad_rate": float}
    """
    config = load_config()
    if enabled is not None:
        config["auto_promote_enabled"] = bool(enabled)
    if ad_rate is not None:
        config["promoted_listing_ad_rate"] = float(ad_rate)
    save_config(config)
    return {
        "auto_promote_enabled": bool(config.get("auto_promote_enabled", True)),
        "promoted_listing_ad_rate": float(config.get("promoted_listing_ad_rate", 7.0)),
    }


def get_promoted_listing_campaign_ids():
    """
    Read promoted listing campaign/ad-group IDs from listingPreferences.json.

    Returns:
        dict: {"campaign_id": str, "ad_group_id": str}
    """
    config = load_config()
    return {
        "campaign_id": config.get("promoted_listing_campaign_id", ""),
        "ad_group_id": config.get("promoted_listing_ad_group_id", ""),
    }


def save_promoted_listing_campaign_ids(campaign_id, ad_group_id):
    """
    Persist promoted listing campaign and ad-group IDs to listingPreferences.json.

    Args:
        campaign_id (str): eBay campaign ID.
        ad_group_id (str): eBay ad group ID.
    """
    config = load_config()
    config["promoted_listing_campaign_id"] = campaign_id
    config["promoted_listing_ad_group_id"] = ad_group_id
    save_config(config)


def clear_promoted_listing_campaign_ids():
    """Reset campaign and ad-group IDs in listingPreferences.json (used on stale campaign recovery)."""
    config = load_config()
    config["promoted_listing_campaign_id"] = ""
    config["promoted_listing_ad_group_id"] = ""
    save_config(config)
```

- [ ] **Step 2: Add the new fields to `listingPreferences.json`**

Open `listingPreferences.json` and add these four fields (insert before the closing `}`):

```json
  "auto_promote_enabled": true,
  "promoted_listing_ad_rate": 7.0,
  "promoted_listing_campaign_id": "",
  "promoted_listing_ad_group_id": ""
```

- [ ] **Step 3: Verify helpers work**

```bash
python -c "
from backend.copyScripts.combine_data import get_promoted_listing_settings, save_promoted_listing_settings, get_promoted_listing_campaign_ids, save_promoted_listing_campaign_ids, clear_promoted_listing_campaign_ids
print(get_promoted_listing_settings())
print(get_promoted_listing_campaign_ids())
save_promoted_listing_settings(enabled=False, ad_rate=5.0)
print(get_promoted_listing_settings())
save_promoted_listing_settings(enabled=True, ad_rate=7.0)
save_promoted_listing_campaign_ids('camp123', 'group456')
print(get_promoted_listing_campaign_ids())
clear_promoted_listing_campaign_ids()
print(get_promoted_listing_campaign_ids())
"
```

Expected:
```
{'auto_promote_enabled': True, 'promoted_listing_ad_rate': 7.0}
{'campaign_id': '', 'ad_group_id': ''}
{'auto_promote_enabled': False, 'promoted_listing_ad_rate': 5.0}
{'campaign_id': 'camp123', 'ad_group_id': 'group456'}
{'campaign_id': '', 'ad_group_id': ''}
```

- [ ] **Step 4: Commit**

```bash
git add backend/copyScripts/combine_data.py listingPreferences.json
git commit -m "feat: add promoted listing preference helpers and JSON fields"
```

---

## Task 3: Create `backend/promoted_listings.py`

**Files:**
- Create: `backend/promoted_listings.py`

This module owns all Marketing API calls. It never touches `listingPreferences.json` directly — callers read/write the IDs.

- [ ] **Step 1: Create the file**

```python
"""
eBay Promoted Listings Standard - Marketing API

Handles campaign creation, ad group creation, and ad enrollment
for the Sell Marketing API v1.

Required OAuth scope: sell.marketing (in addition to sell.inventory)

API base: https://api.ebay.com/sell/marketing/v1
"""

import os
import requests
from datetime import datetime, timezone

MARKETING_API_BASE = "https://api.ebay.com/sell/marketing/v1"
CAMPAIGN_NAME = "AxisResearcher Auto-Promote"


class PromotionError(Exception):
    """Raised when a Marketing API call fails unrecoverably."""
    pass


def _marketing_headers(user_token):
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _create_campaign(user_token, ad_rate):
    """
    Create a new PLS campaign.

    Args:
        user_token (str): eBay user OAuth token with sell.marketing scope.
        ad_rate (float): Ad rate percent (e.g. 7.0).

    Returns:
        str: The new campaignId.

    Raises:
        PromotionError: on API failure.
    """
    start_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "campaignName": CAMPAIGN_NAME,
        "fundingStrategy": {
            "adRatePercent": ad_rate,
            "fundingModel": "COST_PER_SALE",
        },
        "marketplaceId": "EBAY_US",
        "startDate": start_date,
    }
    resp = requests.post(
        f"{MARKETING_API_BASE}/ad_campaign",
        headers=_marketing_headers(user_token),
        json=body,
        timeout=20,
    )
    if resp.status_code == 201:
        campaign_id = resp.json().get("campaignId")
        if not campaign_id:
            raise PromotionError("createCampaign succeeded but returned no campaignId")
        print(f"[promote] Created campaign: {campaign_id}")
        return campaign_id
    raise PromotionError(
        f"createCampaign failed {resp.status_code}: {resp.text[:300]}"
    )


def _create_ad_group(user_token, campaign_id):
    """
    Create the default ad group for a campaign.

    Args:
        user_token (str): eBay user OAuth token.
        campaign_id (str): Campaign to attach the ad group to.

    Returns:
        str: The new adGroupId.

    Raises:
        PromotionError: on API failure.
    """
    body = {
        "campaignId": campaign_id,
        "adGroupName": "Default",
        "defaultBid": {"currency": "USD", "value": "0"},
    }
    resp = requests.post(
        f"{MARKETING_API_BASE}/ad_group",
        headers=_marketing_headers(user_token),
        json=body,
        timeout=20,
    )
    if resp.status_code == 201:
        ad_group_id = resp.json().get("adGroupId")
        if not ad_group_id:
            raise PromotionError("createAdGroup succeeded but returned no adGroupId")
        print(f"[promote] Created ad group: {ad_group_id}")
        return ad_group_id
    raise PromotionError(
        f"createAdGroup failed {resp.status_code}: {resp.text[:300]}"
    )


def _enroll_sku(user_token, campaign_id, ad_group_id, sku):
    """
    Enroll a single SKU in the campaign via bulkCreateAdsByInventoryReference.

    Args:
        user_token (str): eBay user OAuth token.
        campaign_id (str): Target campaign.
        ad_group_id (str): Target ad group.
        sku (str): Seller SKU to enroll.

    Raises:
        PromotionError: on API failure (duplicate ad is silently ignored).
    """
    body = {
        "requests": [
            {
                "adGroupId": ad_group_id,
                "inventoryReferenceId": sku,
                "inventoryReferenceType": "INVENTORY_ITEM",
            }
        ]
    }
    resp = requests.post(
        f"{MARKETING_API_BASE}/ad_campaign/{campaign_id}/bulk_create_ads_by_inventory_reference",
        headers=_marketing_headers(user_token),
        json=body,
        timeout=20,
    )
    if resp.status_code in (200, 207):
        # 207 Multi-Status: check individual result
        data = resp.json()
        responses = data.get("responses", [data])
        for item in responses:
            errors = item.get("errors", [])
            if errors:
                for err in errors:
                    # Duplicate ad is not a real error
                    if "already" in err.get("message", "").lower():
                        print(f"[promote] SKU {sku} already in campaign — skipping")
                        return
                raise PromotionError(
                    f"bulkCreateAds error for SKU {sku}: {errors[0].get('message', str(errors))}"
                )
        print(f"[promote] Enrolled SKU {sku} in campaign {campaign_id}")
        return
    if resp.status_code == 200:
        print(f"[promote] Enrolled SKU {sku} in campaign {campaign_id}")
        return
    raise PromotionError(
        f"bulkCreateAds failed {resp.status_code}: {resp.text[:300]}"
    )


def _is_stale_campaign_error(exc):
    """Return True if the exception message indicates the campaign no longer exists."""
    msg = str(exc).lower()
    return "404" in msg or "not found" in msg


def promote_listing(sku, user_token, campaign_id, ad_group_id, ad_rate):
    """
    Enroll sku in the PLS campaign at ad_rate percent.

    Creates the campaign and ad group if campaign_id is empty.
    If the campaign is stale (404/not found), clears IDs and retries once.

    Args:
        sku (str): Seller SKU to promote.
        user_token (str): eBay user OAuth token with sell.marketing scope.
        campaign_id (str): Existing campaign ID, or "" to create one.
        ad_group_id (str): Existing ad group ID, or "" to create one.
        ad_rate (float): Ad rate percent (e.g. 7.0).

    Returns:
        tuple[str, str]: (campaign_id, ad_group_id) — existing or newly created.

    Raises:
        PromotionError: on unrecoverable failure.
    """
    def _run(cid, gid):
        if not cid:
            cid = _create_campaign(user_token, ad_rate)
            gid = _create_ad_group(user_token, cid)
        _enroll_sku(user_token, cid, gid, sku)
        return cid, gid

    try:
        return _run(campaign_id, ad_group_id)
    except PromotionError as exc:
        if campaign_id and _is_stale_campaign_error(exc):
            print(f"[promote] Campaign {campaign_id} appears stale — recreating")
            return _run("", "")
        raise
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "from backend.promoted_listings import promote_listing; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/promoted_listings.py
git commit -m "feat: add promoted_listings module with Marketing API calls"
```

---

## Task 4: Add settings endpoints to `app.py`

**Files:**
- Modify: `app.py`

The import line (around line 48) already imports many helpers from `combine_data`. We need to add the new ones and two new routes. The routes go after the existing `/api/settings/minimum-images` routes (around line 1987).

- [ ] **Step 1: Add new imports to the `combine_data` import line**

Find the large `from backend.copyScripts.combine_data import (` block near the top of `app.py`. Add these four names to it:

```python
    get_promoted_listing_settings,
    save_promoted_listing_settings,
    get_promoted_listing_campaign_ids,
    save_promoted_listing_campaign_ids,
    clear_promoted_listing_campaign_ids,
```

- [ ] **Step 2: Add two new routes after the minimum-images routes (after line ~1987)**

```python
@app.route('/api/settings/promoted-listings', methods=['GET'])
def api_get_promoted_listing_settings():
    """Read promoted listing enabled flag and ad rate."""
    try:
        return jsonify(get_promoted_listing_settings()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/promoted-listings', methods=['POST'])
def api_save_promoted_listing_settings():
    """Persist promoted listing enabled flag and/or ad rate."""
    body = request.get_json(silent=True) or {}
    enabled = body.get('auto_promote_enabled')
    ad_rate = body.get('promoted_listing_ad_rate')
    try:
        if ad_rate is not None:
            ad_rate = float(ad_rate)
            if ad_rate < 1 or ad_rate > 100:
                return jsonify({'error': 'promoted_listing_ad_rate must be between 1 and 100'}), 400
        result = save_promoted_listing_settings(enabled=enabled, ad_rate=ad_rate)
        return jsonify(result), 200
    except (TypeError, ValueError):
        return jsonify({'error': 'promoted_listing_ad_rate must be a number'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

- [ ] **Step 3: Verify Flask starts without error**

```bash
python app.py &
sleep 2
curl -s http://localhost:5000/api/settings/promoted-listings
kill %1
```

Expected: `{"auto_promote_enabled": true, "promoted_listing_ad_rate": 7.0}`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: add /api/settings/promoted-listings GET and POST routes"
```

---

## Task 5: Call `promote_listing` in the upload route

**Files:**
- Modify: `app.py` — `upload_listing()` function (around line 1775)

- [ ] **Step 1: Add the promoted_listings import at the top of `app.py`**

Find the import block near the top of `app.py` and add:

```python
from backend.promoted_listings import promote_listing, PromotionError
```

- [ ] **Step 2: Add the promotion call inside `upload_listing`'s `generate()` function**

Find the block in `upload_listing` that reads (around line 1775):

```python
            lid = upload_result.get("listingId")
            if lid:
                save_ebay_listing_id(sku=sku, filename=filename, ebay_listing_id=lid)
            else:
                print("[API] Warning: publish succeeded but listingId missing; ebayListingId not saved to JSON")

            yield progress_event('Uploading to eBay', 'completed')

            yield result_event({
                "upload_result": upload_result,
                "error": None
            })
```

Replace it with:

```python
            lid = upload_result.get("listingId")
            if lid:
                save_ebay_listing_id(sku=sku, filename=filename, ebay_listing_id=lid)
            else:
                print("[API] Warning: publish succeeded but listingId missing; ebayListingId not saved to JSON")

            yield progress_event('Uploading to eBay', 'completed')

            # Step 3: Promoted listing enrollment (non-fatal)
            promote_settings = get_promoted_listing_settings()
            if promote_settings.get("auto_promote_enabled"):
                yield progress_event('Enrolling in Promoted Listings', 'in_progress')
                try:
                    ids = get_promoted_listing_campaign_ids()
                    user_token = os.getenv("user_token", "")
                    new_campaign_id, new_ad_group_id = promote_listing(
                        sku=actual_sku,
                        user_token=user_token,
                        campaign_id=ids["campaign_id"],
                        ad_group_id=ids["ad_group_id"],
                        ad_rate=promote_settings["promoted_listing_ad_rate"],
                    )
                    if new_campaign_id != ids["campaign_id"] or new_ad_group_id != ids["ad_group_id"]:
                        save_promoted_listing_campaign_ids(new_campaign_id, new_ad_group_id)
                    yield progress_event('Enrolling in Promoted Listings', 'completed')
                except PromotionError as pe:
                    print(f"[API] Promoted listing enrollment failed: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed: {pe}', 'warning')
                except Exception as pe:
                    print(f"[API] Unexpected error during promotion: {pe}")
                    yield progress_event(f'Promoted listing enrollment failed (unexpected): {pe}', 'warning')

            yield result_event({
                "upload_result": upload_result,
                "error": None
            })
```

- [ ] **Step 3: Verify Flask starts without import errors**

```bash
python -c "import app; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: enroll listing in Promoted Listings after successful upload"
```

---

## Task 6: Settings UI — Promoted Listings section

**Files:**
- Modify: `frontend/src/App.jsx` — Settings tab (around line 3311)

The Settings tab renders inline in `App.jsx`. Add the Promoted Listings section right after the Auto Background Removal section. Follow the exact same pattern: a toggle + a conditional numeric input.

- [ ] **Step 1: Add state variables for promoted listings settings**

In `App.jsx`, find where other settings state is declared (near the top of the component, look for `autoBackgroundRemovalEnabled` or similar). Add:

```jsx
const [autoPromoteEnabled, setAutoPromoteEnabled] = useState(true);
const [promotedListingAdRate, setPromotedListingAdRate] = useState(7.0);
```

- [ ] **Step 2: Add fetch on settings tab load**

Find where the settings tab fetches its initial data (look for a `useEffect` or fetch call that loads `auto-restock` or `minimum-images` settings). Add alongside those:

```jsx
fetch('/api/settings/promoted-listings')
  .then(r => r.json())
  .then(d => {
    if (d.auto_promote_enabled !== undefined) setAutoPromoteEnabled(d.auto_promote_enabled);
    if (d.promoted_listing_ad_rate !== undefined) setPromotedListingAdRate(d.promoted_listing_ad_rate);
  })
  .catch(() => {});
```

- [ ] **Step 3: Add save helpers**

Add these two functions alongside similar save helpers in `App.jsx`:

```jsx
const saveAutoPromoteEnabled = (val) => {
  setAutoPromoteEnabled(val);
  fetch('/api/settings/promoted-listings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ auto_promote_enabled: val }),
  }).catch(() => {});
};

const savePromotedListingAdRate = (val) => {
  setPromotedListingAdRate(val);
  fetch('/api/settings/promoted-listings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ promoted_listing_ad_rate: val }),
  }).catch(() => {});
};
```

- [ ] **Step 4: Add the UI section in the Settings tab**

Find the Auto Background Removal section in the Settings tab JSX. It looks roughly like:

```jsx
{/* Auto Background Removal */}
<div className="...">
  ...toggle...
</div>
```

Add the Promoted Listings section immediately after it, copying the exact same container/layout classes:

```jsx
{/* Promoted Listings */}
<div className="flex flex-col gap-2 py-4 border-b border-border-default">
  <div className="flex items-center justify-between">
    <div className="flex flex-col gap-1">
      <span className="text-text-primary font-medium">Promoted Listings</span>
      <span className="text-text-secondary text-sm">
        Auto-enroll new listings in a Promoted Listings campaign.
        Requires eBay re-authorization with <code>sell.marketing</code> scope.
      </span>
    </div>
    <button
      onClick={() => saveAutoPromoteEnabled(!autoPromoteEnabled)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        autoPromoteEnabled ? 'bg-blue-500' : 'bg-surface-raised'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          autoPromoteEnabled ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  </div>
  {autoPromoteEnabled && (
    <div className="flex items-center gap-2 mt-1">
      <span className="text-text-secondary text-sm">Ad Rate:</span>
      <input
        type="number"
        min={1}
        max={100}
        step={0.1}
        value={promotedListingAdRate}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          if (!isNaN(v) && v >= 1 && v <= 100) savePromotedListingAdRate(v);
        }}
        className="w-20 px-2 py-1 rounded border border-border-default bg-surface-panel text-text-primary text-sm"
      />
      <span className="text-text-secondary text-sm">%</span>
    </div>
  )}
</div>
```

> **Note:** Look at the actual toggle markup used for Auto Background Removal in `App.jsx` and match its exact classes. The snippet above is a reference pattern — adapt if the codebase uses a shared `Toggle` component.

- [ ] **Step 5: Start the dev server and verify the Settings tab**

```bash
npm run dev
```

Open `http://localhost:4000`, go to Settings. Verify:
- "Promoted Listings" section appears after "Auto Background Removal"
- Toggle starts ON (default)
- "Ad Rate: 7.0 %" input is visible when toggle is ON
- Input disappears when toggle is toggled OFF
- Changes persist (reload page, values match)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add Promoted Listings section to Settings tab"
```

---

## Task 7: End-to-end smoke test

This task is manual — no automated test suite exists in the project.

- [ ] **Step 1: Check current token has sell.marketing scope (or note it doesn't)**

```bash
python testing/test_update_tokens.py verify
```

If the token was issued before the scope change, the Marketing API calls will fail with a 403. This is expected and shows as a non-fatal warning. Re-auth is needed for a full end-to-end pass.

- [ ] **Step 2: Re-authorize to include `sell.marketing`**

```bash
python -m backend.refreshToken open-consent
# Complete consent in browser, copy the code from the redirect URL
python testing/test_update_tokens.py exchange <code>
```

- [ ] **Step 3: Run a test upload**

Start the app (`npm run dev`), upload a listing through the normal UI workflow. Watch server logs for:
```
[promote] Created campaign: <id>
[promote] Created ad group: <id>
[promote] Enrolled SKU AXIS_xx in campaign <id>
```

- [ ] **Step 4: Verify campaign IDs were persisted**

```bash
python -c "from backend.copyScripts.combine_data import get_promoted_listing_campaign_ids; print(get_promoted_listing_campaign_ids())"
```

Expected: non-empty `campaign_id` and `ad_group_id`.

- [ ] **Step 5: Verify a second upload reuses the same campaign (no new campaign created)**

Upload a second listing. Server logs should show only:
```
[promote] Enrolled SKU AXIS_yy in campaign <same id>
```
No "Created campaign" line.

- [ ] **Step 6: Verify non-fatal failure path**

Temporarily set a bad `user_token` in `.env`, run another upload. Confirm the upload still succeeds and the frontend shows a warning message, not an error.

Restore the good token afterward.
