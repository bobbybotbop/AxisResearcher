"""
Copy Seller research pipeline: collect a seller's best listings, compute raw
demand metrics per Product Candidate, and stream progress as event dicts.

The eBay Browse API boundary lives in single_search_by_query plus the reused
getItemIds / single_get_detailed_item_data from backend.ebay_cli. Everything
else is pure and unit-tested without network access.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone

import requests

from backend.ebay_cli import (
    browse_api_headers,
    getItemIds,
    single_get_detailed_item_data,
)
from backend.helper_functions import helper_get_valid_token
from backend.logger import log_event

DAILY_API_BUDGET = 5000
# Seller setup = one getItemIds page (conservative: sellers can need several).
SELLER_SETUP_CALLS = 5

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_USAGE_FILE = os.path.join(_PROJECT_ROOT, "Collected-Data", "ebay_api_usage.json")


# ---------------------------------------------------------------------------
# Pure metric functions
# ---------------------------------------------------------------------------

def compute_sold_velocity(estimated_sold, item_creation_date, now=None):
    """estimatedSoldQuantity ÷ listing age in days (minimum age: 1 day).

    Returns None when the creation date is missing or unparseable.
    """
    if not item_creation_date:
        return None
    try:
        created = datetime.fromisoformat(str(item_creation_date).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    age_days = max((now - created).total_seconds() / 86400.0, 1.0)
    return estimated_sold / age_days


def compute_demand_coefficient(top_k_sold_sum, active_listing_total):
    """Top-K sold-sum ÷ active-listing total; 0 when there are no actives."""
    if not active_listing_total:
        return 0.0
    return top_k_sold_sum / active_listing_total


def select_top_listings(detailed_items, min_sold, top_n):
    """Drop listings below min_sold, sort by sold desc, cap at top_n."""
    eligible = [
        item for item in detailed_items
        if (item.get("estimatedSoldQuantity") or 0) >= min_sold
    ]
    eligible.sort(key=lambda item: item.get("estimatedSoldQuantity") or 0, reverse=True)
    return eligible[:top_n]


def simplify_title_to_phrase(title):
    """Deterministic stub: lowercase, strip punctuation, first 6 words.

    Ticket 07 replaces the internals with the real title-simplification
    prompt; callers must keep going through this single function.
    """
    words = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower()).split()
    return " ".join(words[:6])


def estimate_api_call_cost(top_n, k):
    """≈ N×(1+K) + seller setup (one getItem per listing + one search per phrase)."""
    return top_n * (1 + k) + SELLER_SETUP_CALLS


# ---------------------------------------------------------------------------
# Daily eBay API-call usage tracking
# ---------------------------------------------------------------------------

class ApiUsageTracker:
    """Persists per-day eBay API-call usage; warns/blocks against the budget."""

    def __init__(self, storage_path=None, daily_budget=DAILY_API_BUDGET):
        self._path = storage_path or _USAGE_FILE
        self.daily_budget = daily_budget
        self._lock = threading.Lock()
        self._date, self._used = self._load()

    @staticmethod
    def _today(now=None):
        return (now or datetime.now(timezone.utc)).date().isoformat()

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                state = json.load(f)
            return state.get("date", self._today()), int(state.get("used", 0))
        except (OSError, ValueError):
            return self._today(), 0

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"date": self._date, "used": self._used}, f)

    def _rollover_if_new_day(self, now=None):
        today = self._today(now)
        if self._date != today:
            self._date, self._used = today, 0
            self._save()

    @property
    def used_today(self):
        with self._lock:
            self._rollover_if_new_day()
            return self._used

    def would_exceed(self, planned_calls):
        with self._lock:
            self._rollover_if_new_day()
            return self._used + planned_calls > self.daily_budget

    def record(self, calls):
        with self._lock:
            self._rollover_if_new_day()
            self._used += calls
            self._save()


# ---------------------------------------------------------------------------
# eBay Browse API boundary
# ---------------------------------------------------------------------------

def single_search_by_query(query, limit=50):
    """Search eBay by keyword phrase. Returns {total_items, items} or None."""
    valid_token = helper_get_valid_token()
    if not valid_token:
        print("❌ Error: Could not get valid access token")
        return None

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    params = {
        "q": query,
        "limit": min(limit, 200),
        "offset": 0,
        "fieldgroups": "EXTENDED",
        "sort": "BEST_MATCH",
    }

    try:
        response = requests.get(
            url, headers=browse_api_headers(valid_token), params=params, timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return {"total_items": data.get("total", 0), "items": data.get("itemSummaries", [])}
        print(f"❌ Phrase search failed: {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Error searching phrase '{query}': {e}")
        return None


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def run_copy_seller(seller_username, top_n=25, k=20, min_sold=1):
    """Run the Copy Seller pipeline, yielding progress/result/error event dicts.

    Emits raw (unranked) Product Candidates; ranking happens client-side from
    these cached metrics plus the user's current weights.
    """
    tracker = ApiUsageTracker()
    estimated_cost = estimate_api_call_cost(top_n, k)

    yield {
        "type": "progress",
        "step": "Checking API budget",
        "status": "in_progress",
        "used_today": tracker.used_today,
        "estimated_cost": estimated_cost,
    }
    if tracker.would_exceed(estimated_cost):
        yield {
            "type": "error",
            "error": (
                f"Daily eBay API budget would be exceeded: "
                f"{tracker.used_today} used + ~{estimated_cost} needed "
                f"> {tracker.daily_budget}/day. Try a smaller N/K or wait until tomorrow."
            ),
        }
        return
    yield {"type": "progress", "step": "Checking API budget", "status": "completed"}

    log_event("copy_seller_run", "started", seller=seller_username, top_n=top_n, k=k, min_sold=min_sold)
    calls_made = 0
    try:
        yield {"type": "progress", "step": "Collecting seller listings", "status": "in_progress"}
        item_ids = getItemIds(seller_username) or []
        calls_made += max(1, -(-len(item_ids) // 200))
        yield {
            "type": "progress",
            "step": "Collecting seller listings",
            "status": "completed",
            "total_listings": len(item_ids),
        }
        if not item_ids:
            yield {"type": "error", "error": f"No listings found for seller '{seller_username}'"}
            return

        yield {"type": "progress", "step": "Fetching listing details", "status": "in_progress"}
        detailed = []
        for item_id in item_ids:
            item = single_get_detailed_item_data(item_id, verbose=False)
            calls_made += 1
            if item:
                detailed.append(item)
        yield {
            "type": "progress",
            "step": "Fetching listing details",
            "status": "completed",
            "fetched": len(detailed),
        }

        top_listings = select_top_listings(detailed, min_sold=min_sold, top_n=top_n)
        if not top_listings:
            yield {"type": "error", "error": f"No listings at or above min-sold threshold ({min_sold})"}
            return

        candidates = []
        for index, item in enumerate(top_listings, start=1):
            title = item.get("title", "")
            phrase = simplify_title_to_phrase(title)
            yield {
                "type": "progress",
                "step": f"Computing metrics ({index}/{len(top_listings)})",
                "status": "in_progress",
                "title": title,
                "search_phrase": phrase,
            }

            search = single_search_by_query(phrase, limit=k) or {"total_items": 0, "items": []}
            calls_made += 1
            active_total = search["total_items"]
            top_k_sold_sum = sum(
                (r.get("estimatedSoldQuantity") or 0) for r in search["items"][:k]
            )

            candidates.append({
                "listing_url": item.get("itemWebUrl", ""),
                "title": title,
                "search_phrase": phrase,
                "estimated_sold_quantity": item.get("estimatedSoldQuantity") or 0,
                "item_creation_date": item.get("itemCreationDate"),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "image_url": (item.get("image") or {}).get("imageUrl"),
                "demand_coefficient": compute_demand_coefficient(top_k_sold_sum, active_total),
                "competition_count": active_total,
                "sold_velocity": compute_sold_velocity(
                    item.get("estimatedSoldQuantity") or 0, item.get("itemCreationDate")
                ),
            })
            yield {
                "type": "progress",
                "step": f"Computing metrics ({index}/{len(top_listings)})",
                "status": "completed",
                "search_phrase": phrase,
            }

        tracker.record(calls_made)
        log_event(
            "copy_seller_run", "completed",
            seller=seller_username, candidates=len(candidates), api_calls=calls_made,
        )
        yield {
            "type": "result",
            "data": {
                "seller": seller_username,
                "inputs": {"top_n": top_n, "k": k, "min_sold": min_sold},
                "api_calls_made": calls_made,
                "api_calls_used_today": tracker.used_today,
                "product_candidates": candidates,
            },
        }
    except Exception as e:
        tracker.record(calls_made)
        log_event("copy_seller_run", "failed", seller=seller_username, error=str(e))
        yield {"type": "error", "error": f"Copy Seller run failed: {e}"}
