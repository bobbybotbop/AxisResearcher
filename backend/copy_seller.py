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
from datetime import datetime, timedelta, timezone

import requests

from backend.copyScripts.combine_data import load_config, save_config
from backend.ebay_cli import (
    _extract_listing_id,
    browse_api_headers,
    getItemIds,
    single_get_detailed_item_data,
)
from backend.helper_functions import helper_get_valid_token
from backend.logger import log_event
from backend.constants.research import (
    DAILY_API_BUDGET,
    SELLER_SETUP_CALLS,
    DEFAULT_TITLE_MAX_WORDS,
    DEFAULT_TITLE_STOPWORDS,
)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COLLECTED_DATA_DIR = os.path.join(_PROJECT_ROOT, "Collected-Data")
_USAGE_FILE = os.path.join(_COLLECTED_DATA_DIR, "ebay_api_usage.json")


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


def _extract_sold_quantity(item):
    """Estimated sold quantity from a getItem response.

    The real getItem shape nests it under estimatedAvailabilities[0]; fall back
    to a top-level estimatedSoldQuantity when present.
    """
    availabilities = item.get("estimatedAvailabilities") or []
    if availabilities:
        sold = availabilities[0].get("estimatedSoldQuantity")
        if sold is not None:
            return sold
    return item.get("estimatedSoldQuantity")


def select_top_listings(detailed_items, min_sold, top_n):
    """Drop listings below min_sold, sort by sold desc, cap at top_n."""
    eligible = [
        item for item in detailed_items
        if (_extract_sold_quantity(item) or 0) >= min_sold
    ]
    eligible.sort(key=lambda item: _extract_sold_quantity(item) or 0, reverse=True)
    return eligible[:top_n]


def _parse_item_creation_date(item_creation_date):
    """Parse an eBay itemCreationDate ISO string to an aware datetime.

    Same parsing approach as compute_sold_velocity. Returns None when missing
    or unparseable.
    """
    if not item_creation_date:
        return None
    try:
        created = datetime.fromisoformat(str(item_creation_date).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created


def filter_listings_by_date_posted(detailed_items, date_posted_start=None, date_posted_end=None):
    """Keep only listings whose itemCreationDate falls within [start, end].

    Both bounds are calendar dates (YYYY-MM-DD strings), inclusive — the end
    date covers the whole day. Listings with a missing/unparseable creation
    date are excluded when a range is given. With no range, returns the input
    unchanged. Applied before the top-N cut and before metric computation.
    """
    if not date_posted_start and not date_posted_end:
        return detailed_items
    start_dt = None
    end_dt = None
    if date_posted_start:
        start_dt = datetime.fromisoformat(str(date_posted_start)).replace(tzinfo=timezone.utc)
    if date_posted_end:
        # Inclusive of the whole end day: bound at the start of the next day.
        end_day = datetime.fromisoformat(str(date_posted_end)).replace(tzinfo=timezone.utc)
        end_dt = end_day + timedelta(days=1)
    kept = []
    for item in detailed_items:
        created = _parse_item_creation_date(item.get("itemCreationDate"))
        if created is None:
            continue
        if start_dt and created < start_dt:
            continue
        if end_dt and created >= end_dt:
            continue
        kept.append(item)
    return kept


# ---------------------------------------------------------------------------
# Title simplification (ticket 07) — single swappable seam
# ---------------------------------------------------------------------------

def get_title_simplification_config():
    """Read the title-simplification config from listingPreferences.json.

    Returns {"stopwords": [...], "max_words": int} — the editable knobs behind
    the deterministic trim, surfaced in the Testing tab.
    """
    config = load_config()
    stopwords = config.get("title_simplification_stopwords", DEFAULT_TITLE_STOPWORDS)
    max_words = config.get("title_simplification_max_words", DEFAULT_TITLE_MAX_WORDS)
    return {"stopwords": list(stopwords), "max_words": int(max_words)}


def save_title_simplification_config(stopwords=None, max_words=None):
    """Persist title-simplification config to listingPreferences.json.

    Args (all optional; unchanged when None):
        stopwords (list[str]): sales terms stripped from titles.
        max_words (int): cap on the simplified phrase length.

    Returns the full config reflecting the saved state.

    Raises ValueError on any invalid provided value.
    """
    config = load_config()
    if stopwords is not None:
        if not isinstance(stopwords, (list, tuple)) or \
                not all(isinstance(w, str) for w in stopwords):
            raise ValueError("stopwords must be a list of strings")
        config["title_simplification_stopwords"] = [w.strip().lower() for w in stopwords if w.strip()]
    if max_words is not None:
        try:
            max_words = int(max_words)
        except (TypeError, ValueError):
            raise ValueError("max_words must be an integer")
        if max_words < 1:
            raise ValueError("max_words must be at least 1")
        config["title_simplification_max_words"] = max_words
    save_config(config)
    return get_title_simplification_config()


def _deterministic_trim(title, config):
    """Offline fallback: lowercase, strip punctuation, drop sales terms, cap words.

    Standalone numeric tokens are treated as quantities/sizes and dropped —
    they make a search phrase too specific without naming the product.
    """
    words = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower()).split()
    stopwords = set(config["stopwords"])
    kept = [w for w in words if w not in stopwords and not w.isdigit()]
    return " ".join(kept[:config["max_words"]])


def simplify_title_to_phrase(title, config=None):
    """Reduce a listing title to a short, common search phrase.

    This is the single swappable seam for title simplification. Today it runs
    the deterministic offline trim; the real prompt (backlog ticket 01) slots
    in here later without touching the pipeline. Callers must keep going
    through this function.
    """
    if config is None:
        config = get_title_simplification_config()
    return _deterministic_trim(title, config)


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
# Pipeline Run persistence (ticket 06)
#
# Each completed run is saved as JSON under Collected-Data/<seller>/runs/
# <timestamp>.json so past runs can be listed, reloaded, and re-ranked
# client-side without re-running the pipeline.
# ---------------------------------------------------------------------------

def _safe_seller_dirname(seller_username):
    """Filesystem-safe seller folder name (ebay_cli convention)."""
    return seller_username.replace(" ", "_").replace("/", "_").replace("\\", "_")


def save_pipeline_run(run, storage_root=None, now=None):
    """Persist one Pipeline Run as JSON; returns the saved record.

    `run` carries seller, inputs, and product_candidates; this adds run_id and
    timestamp. Written to <storage_root>/<seller>/runs/<run_id>.json. Any
    legacy `weights` field on the record is dropped — ranking weights are no
    longer part of a Pipeline Run.
    """
    root = storage_root or _COLLECTED_DATA_DIR
    now = now or datetime.now(timezone.utc)
    timestamp = now.isoformat()
    run_id = now.strftime("%Y%m%d_%H%M%S_%f")
    record = {k: v for k, v in run.items() if k != "weights"}
    record = {**record, "run_id": run_id, "timestamp": timestamp}

    runs_dir = os.path.join(root, _safe_seller_dirname(run["seller"]), "runs")
    os.makedirs(runs_dir, exist_ok=True)
    path = os.path.join(runs_dir, f"{run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return record


def _run_summaries(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            path = os.path.join(dirpath, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    run = json.load(f)
            except (OSError, ValueError):
                continue
            yield run


def list_pipeline_runs(storage_root=None):
    """List past Pipeline Runs as summaries (newest first).

    Summary shape: run_id, seller, timestamp, candidate_count. Legacy runs
    carrying a `weights` field still load; the weights are ignored.
    """
    root = storage_root or _COLLECTED_DATA_DIR
    if not os.path.isdir(root):
        return []
    summaries = [
        {
            "run_id": run.get("run_id", ""),
            "seller": run.get("seller", ""),
            "timestamp": run.get("timestamp", ""),
            "candidate_count": len(run.get("product_candidates") or []),
        }
        for run in _run_summaries(root)
        if "product_candidates" in run
    ]
    summaries.sort(key=lambda s: s["timestamp"], reverse=True)
    return summaries


def load_pipeline_run(run_id, storage_root=None):
    """Load one full Pipeline Run (input + candidates) by run_id.

    Legacy runs carrying a `weights` field still load; the weights are ignored
    (dropped from the returned record).
    """
    root = storage_root or _COLLECTED_DATA_DIR
    if not os.path.isdir(root):
        return None
    for run in _run_summaries(root):
        if run.get("run_id") == run_id:
            return {k: v for k, v in run.items() if k != "weights"}
    return None


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

def run_copy_seller(seller_username, top_n=25, k=20, min_sold=1,
                    date_posted_start=None, date_posted_end=None,
                    storage_root=None):
    """Run the Copy Seller pipeline, yielding progress/result/error event dicts.

    Emits raw Product Candidates with their collected metrics; ordering happens
    client-side by one user-picked metric. On completion the Pipeline Run
    (input + candidates) is persisted under Collected-Data/<seller>/runs/ and
    the milestone is logged.

    date_posted_start / date_posted_end (YYYY-MM-DD) bound the seller's own
    listings by itemCreationDate — a collection-time filter applied before the
    top-N cut and before any metric is computed.
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

        # Date-posted range filter (ticket 12): collection-time filter on the
        # seller's own listings, applied before the top-N cut and before any
        # metric is computed.
        date_filtered = filter_listings_by_date_posted(
            detailed,
            date_posted_start=date_posted_start,
            date_posted_end=date_posted_end,
        )
        if not date_filtered:
            yield {
                "type": "error",
                "error": (
                    f"No listings posted within the date range "
                    f"{date_posted_start or '…'} → {date_posted_end or '…'}"
                ),
            }
            return

        top_listings = select_top_listings(date_filtered, min_sold=min_sold, top_n=top_n)
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
            # itemSummaries carry no sold data; fetch each top-K result's getItem
            # detail and sum estimatedSoldQuantity (the N×(1+K) cost model).
            top_k_sold_sum = 0
            for result in search["items"][:k]:
                legacy_id = _extract_listing_id(result.get("itemId"))
                if not legacy_id:
                    continue
                detail = single_get_detailed_item_data(f"v1|{legacy_id}|0", verbose=False)
                calls_made += 1
                if detail:
                    top_k_sold_sum += _extract_sold_quantity(detail) or 0

            candidates.append({
                "listing_url": item.get("itemWebUrl", ""),
                "title": title,
                "search_phrase": phrase,
                "estimated_sold_quantity": _extract_sold_quantity(item) or 0,
                "item_creation_date": item.get("itemCreationDate"),
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "image_url": (item.get("image") or {}).get("imageUrl"),
                "demand_coefficient": compute_demand_coefficient(top_k_sold_sum, active_total),
                "competition_count": active_total,
                "sold_velocity": compute_sold_velocity(
                    _extract_sold_quantity(item) or 0, item.get("itemCreationDate")
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
        saved_run = save_pipeline_run(
            {
                "seller": seller_username,
                "inputs": {
                    "top_n": top_n, "k": k, "min_sold": min_sold,
                    "date_posted_start": date_posted_start,
                    "date_posted_end": date_posted_end,
                },
                "product_candidates": candidates,
            },
            storage_root=storage_root,
        )
        log_event(
            "copy_seller_run", "saved",
            seller=seller_username, run_id=saved_run["run_id"], candidates=len(candidates),
        )
        yield {
            "type": "result",
            "data": {
                "seller": seller_username,
                "run_id": saved_run["run_id"],
                "timestamp": saved_run["timestamp"],
                "inputs": {
                    "top_n": top_n, "k": k, "min_sold": min_sold,
                    "date_posted_start": date_posted_start,
                    "date_posted_end": date_posted_end,
                },
                "api_calls_made": calls_made,
                "api_calls_used_today": tracker.used_today,
                "product_candidates": candidates,
            },
        }
    except Exception as e:
        tracker.record(calls_made)
        log_event("copy_seller_run", "failed", seller=seller_username, error=str(e))
        yield {"type": "error", "error": f"Copy Seller run failed: {e}"}
