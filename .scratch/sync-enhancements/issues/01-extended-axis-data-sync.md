# Extended AXIS_ data sync from eBay

Status: open
Type: task

## Summary

When syncing active listings from eBay via `GetSellerList`, the current implementation only updates a subset of fields for AXIS_ listings (title, description, images, condition, quantity, price). Several structured fields that eBay may have updated are not synced back.

## Fields to sync

The following fields should be fetched from eBay and merged into the local AXIS_ JSON files during sync:

- `inventoryItem.packageWeightAndSize` (weight and package dimensions)
- `offer.listingPolicies` (fulfillment, payment, return policy IDs)
- `offer.categoryId`
- `offer.merchantLocationKey`
- `inventoryItem.product.aspects` (item specifics)

## Approach

`GetSellerList` (Trading API) does not return all of these fields. Options:

1. **Sell Inventory API**: For each active AXIS_ SKU, call `GET /sell/inventory/v1/inventory_item/{sku}` and `GET /sell/inventory/v1/offer?sku={sku}` to get the full structured data. More API calls but gives complete data.
2. **GetItem (Trading API)**: Call `GetItem` per item ID for full listing details including shipping and policies. Also more API calls.
3. **Hybrid**: Use `GetSellerList` for the common fields (already done), add per-item calls only for listings where the user requests a full refresh.

## Context

- Current sync implementation: `POST /api/listings/sync-active` in `app.py`
- AXIS_ merge logic: around line 2700+ in `app.py`
- `get_seller_list()` in `backend/ebay_cli.py` returns: `item_id, seller_sku, title, quantity, price, image_urls, condition, start_time, description, is_variation`
