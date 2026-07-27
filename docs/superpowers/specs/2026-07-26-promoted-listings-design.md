# Promoted Listings - Design Spec

**Date:** 2026-07-26
**Status:** Approved

## Overview

After every successful listing upload, automatically enroll the listing in a Promoted Listings Standard (PLS) campaign on eBay using a configurable ad rate. The feature is toggled and configured via the Settings tab. A single reusable campaign is created once and reused for all subsequent uploads.

## Architecture & Data Flow

### New fields in `listingPreferences.json`

```json
{
  "auto_promote_enabled": true,
  "promoted_listing_ad_rate": 7.0,
  "promoted_listing_campaign_id": ""
}
```

- `auto_promote_enabled` - whether to enroll new listings. Default: `true`.
- `promoted_listing_ad_rate` - ad rate as a percentage (0.1-100). Default: `7.0`.
- `promoted_listing_campaign_id` - eBay campaign ID, written once on first campaign creation, read on every subsequent upload. Empty string means no campaign exists yet. Not exposed to the frontend.
- `promoted_listing_ad_group_id` - eBay ad group ID for the campaign's default ad group, written once alongside campaign creation. Not exposed to the frontend.

### Upload flow change

After `upload_complete_listing` returns a `listingId`, `app.py` checks `auto_promote_enabled`. If true, it calls `promote_listing()` from `backend/promoted_listings.py`, passing the SKU, user token, current campaign ID (may be empty), and ad rate. The returned campaign ID is persisted back to `listingPreferences.json` if it changed.

```
upload_complete_listing(sku) -> listingId
  if auto_promote_enabled:
    campaign_id = promote_listing(sku, user_token, campaign_id, ad_rate)
    persist campaign_id to listingPreferences.json
    stream progress_event with outcome
```

### API call sequence (per upload)

1. If no `promoted_listing_campaign_id`: call `POST /sell/marketing/v1/ad_campaign` to create a "AxisResearcher Auto-Promote" PLS campaign. Persist campaign ID.
2. Call `POST /sell/marketing/v1/ad_campaign/{campaignId}/bulk_create_ads_by_inventory_reference` with the SKU.

### eBay API endpoints used

| Call | Method | URL |
|------|--------|-----|
| Create campaign | POST | `https://api.ebay.com/sell/marketing/v1/ad_campaign` |
| Create ad group | POST | `https://api.ebay.com/sell/marketing/v1/ad_group` |
| Enroll listing | POST | `https://api.ebay.com/sell/marketing/v1/ad_campaign/{campaignId}/bulk_create_ads_by_inventory_reference` |

**`createCampaign` request body (key fields):**
```json
{
  "campaignName": "AxisResearcher Auto-Promote",
  "fundingStrategy": {
    "adRatePercent": 7.0,
    "fundingModel": "COST_PER_SALE"
  },
  "marketplaceId": "EBAY_US",
  "startDate": "<ISO 8601 campaign start>"
}
```
No `endDate` - campaign runs indefinitely.

**`createAdGroup` request body:**
```json
{
  "campaignId": "<campaignId>",
  "adGroupName": "Default",
  "defaultBid": { "currency": "USD", "value": "0" }
}
```
PLS Standard campaigns require at least one ad group. The ad group ID is stored alongside the campaign ID in `listingPreferences.json` as `promoted_listing_ad_group_id`.

**`bulkCreateAdsByInventoryReference` request body:**
```json
{
  "requests": [{
    "adGroupId": "<adGroupId>",
    "inventoryReferenceId": "<sku>",
    "inventoryReferenceType": "INVENTORY_ITEM"
  }]
}

**Required OAuth scope:** `sell.marketing` (added alongside the existing `sell.inventory` scope - requires one-time user re-authorization via the existing consent flow).

### New file: `backend/promoted_listings.py`

All Marketing API logic is isolated here. Public interface:

```python
def promote_listing(sku: str, user_token: str, campaign_id: str, ad_group_id: str, ad_rate: float) -> tuple[str, str]:
    """
    Enrolls sku in the PLS campaign at ad_rate percent.
    Creates the campaign and ad group if campaign_id is empty.
    Returns (campaign_id, ad_group_id) - existing or newly created.
    Raises PromotionError on unrecoverable failure.
    """
```

`upload_to_ebay.py` is not changed. The call to `promote_listing` is made in `app.py` after `upload_complete_listing` succeeds, keeping promotion separate from the inventory upload logic.

## Settings UI

A new "Promoted Listings" section in the Settings tab, placed after "Auto Background Removal":

```
Promoted Listings
  [toggle]  Auto-promote new listings
  Ad Rate:  [ 7.0 ]%   (numeric input, disabled when toggle is off)
```

- Toggle maps to `auto_promote_enabled`.
- Numeric input: step 0.1, min 1, max 100, disabled/greyed when toggle is off.
- A note below: "Requires eBay re-authorization with sell.marketing scope. See eBay Token Management."
- Read on settings tab load from `GET /api/settings/promoted-listings`.
- Written on change (same debounce/save pattern as minimum-images) via `POST /api/settings/promoted-listings`.

## Backend Settings Endpoints

**`GET /api/settings/promoted-listings`**
Returns:
```json
{ "auto_promote_enabled": true, "promoted_listing_ad_rate": 7.0 }
```

**`POST /api/settings/promoted-listings`**
Accepts (any subset):
```json
{ "auto_promote_enabled": true, "promoted_listing_ad_rate": 7.0 }
```
Writes to `listingPreferences.json`. Returns updated values.

`promoted_listing_campaign_id` is not exposed via any settings endpoint.

## Error Handling

**Promotion is non-fatal.** If any Marketing API call fails, the upload is still reported as successful. A warning is streamed via a `progress_event`:
```
"Listing uploaded. Promoted listing enrollment failed: <reason>"
```

**Campaign gone.** If the campaign ID is stale (eBay returns 404 or "campaign not found"), the code clears both `promoted_listing_campaign_id` and `promoted_listing_ad_group_id` from `listingPreferences.json` and retries once by creating a new campaign and ad group.

**Duplicate ad.** If eBay returns an error indicating the SKU is already enrolled in the campaign, it is silently ignored.

**Missing `sell.marketing` scope.** 401 from Marketing API surfaces as the non-fatal warning. The user is directed to re-authorize via the eBay Token Management section in Settings.

**Ad rate changes.** Changing `promoted_listing_ad_rate` in Settings applies to new uploads only. Existing enrolled ads are not retroactively updated.

## OAuth Scope Addition

The `sell.marketing` scope must be appended to the eBay authorization URL constructed in `backend/refreshToken.py`. The user must run the consent flow once:

```
python -m backend.refreshToken open-consent
# approve in browser
python testing/test_update_tokens.py exchange <code>
```

No other changes to the token infrastructure.
