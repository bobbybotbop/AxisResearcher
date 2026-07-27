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
