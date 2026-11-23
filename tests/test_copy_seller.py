"""
Tests for the Copy Seller research pipeline backend (backend/copy_seller.py).

All eBay API calls are mocked — these tests never hit the network. Pure metric
functions are tested against worked examples from the spec; the orchestration
is tested at the run_copy_seller seam with the eBay boundary mocked.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import copy_seller


# ---------------------------------------------------------------------------
# compute_sold_velocity
# ---------------------------------------------------------------------------

def test_sold_velocity_divides_sold_by_age_in_days():
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)
    created = (now - timedelta(days=10)).isoformat()
    assert copy_seller.compute_sold_velocity(100, created, now=now) == pytest.approx(10.0)


def test_sold_velocity_parses_ebay_z_suffix_timestamp():
    now = datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)
    created = "2026-11-11T12:00:00.000Z"  # 10 days before now
    assert copy_seller.compute_sold_velocity(50, created, now=now) == pytest.approx(5.0)


def test_sold_velocity_minimum_age_is_one_day():
    # A listing created moments ago must not divide by zero.
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)
    created = now.isoformat()
    assert copy_seller.compute_sold_velocity(7, created, now=now) == pytest.approx(7.0)


def test_sold_velocity_missing_creation_date_returns_none():
    now = datetime(2026, 11, 21, tzinfo=timezone.utc)
    assert copy_seller.compute_sold_velocity(7, None, now=now) is None


# ---------------------------------------------------------------------------
# compute_demand_coefficient
# ---------------------------------------------------------------------------

def test_demand_coefficient_is_sold_sum_over_active_total():
    assert copy_seller.compute_demand_coefficient(200, 50) == pytest.approx(4.0)


def test_demand_coefficient_zero_active_returns_zero():
    assert copy_seller.compute_demand_coefficient(200, 0) == 0.0


# ---------------------------------------------------------------------------
# _extract_sold_quantity
# ---------------------------------------------------------------------------

def test_extract_sold_quantity_reads_estimated_availabilities():
    item = {"estimatedAvailabilities": [{"estimatedSoldQuantity": 42}]}
    assert copy_seller._extract_sold_quantity(item) == 42


def test_extract_sold_quantity_falls_back_to_top_level():
    assert copy_seller._extract_sold_quantity({"estimatedSoldQuantity": 7}) == 7


def test_extract_sold_quantity_missing_returns_none():
    assert copy_seller._extract_sold_quantity({}) is None
    assert copy_seller._extract_sold_quantity({"estimatedAvailabilities": []}) is None


# ---------------------------------------------------------------------------
# select_top_listings
# ---------------------------------------------------------------------------

def _listing(item_id, sold, title="t", created="2026-01-01T00:00:00.000Z"):
    # Realistic getItem shape: sold quantity lives under estimatedAvailabilities.
    return {
        "itemId": item_id,
        "title": title,
        "estimatedAvailabilities": [{"estimatedSoldQuantity": sold}],
        "itemCreationDate": created,
        "itemWebUrl": f"https://www.ebay.com/itm/{item_id}",
    }


def test_select_top_listings_skips_below_min_sold_and_caps_at_n():
    items = [_listing(str(i), sold) for i, sold in enumerate([0, 1, 5, 3, 100, 2])]
    selected = copy_seller.select_top_listings(items, min_sold=2, top_n=3)
    assert [copy_seller._extract_sold_quantity(l) for l in selected] == [100, 5, 3]


def test_select_top_listings_sorts_descending_by_sold():
    items = [_listing("a", 4), _listing("b", 9), _listing("c", 1)]
    selected = copy_seller.select_top_listings(items, min_sold=1, top_n=25)
    assert [l["itemId"] for l in selected] == ["b", "a", "c"]


# ---------------------------------------------------------------------------
# simplify_title_to_phrase (stub contract — ticket 07 owns the real prompt)
# ---------------------------------------------------------------------------

def test_simplify_title_to_phrase_returns_deterministic_short_phrase():
    title = "  3D Printed Dragon Bookend - Purple & Gold, New Condition!  "
    phrase = copy_seller.simplify_title_to_phrase(title)
    assert isinstance(phrase, str)
    assert phrase == phrase.lower()
    assert "  " not in phrase
    assert phrase == copy_seller.simplify_title_to_phrase(title)  # deterministic
    assert len(phrase.split()) <= 6


# ---------------------------------------------------------------------------
# API budget: estimate + daily usage tracker
# ---------------------------------------------------------------------------

def test_estimate_api_call_cost_matches_spec_formula():
    # ≈ N×(1+K) + seller setup; ~600 calls for N=25, K=20 → 25*21 = 525 + setup
    assert copy_seller.estimate_api_call_cost(25, 20) == 525 + copy_seller.SELLER_SETUP_CALLS


def test_api_usage_tracker_blocks_run_that_would_exceed_daily_budget(tmp_path):
    tracker = copy_seller.ApiUsageTracker(
        storage_path=str(tmp_path / "usage.json"), daily_budget=5000
    )
    tracker.record(4800)
    assert tracker.would_exceed(300) is True
    assert tracker.would_exceed(199) is False


def test_api_usage_tracker_resets_on_new_day(tmp_path):
    tracker = copy_seller.ApiUsageTracker(
        storage_path=str(tmp_path / "usage.json"), daily_budget=5000
    )
    tracker.record(4900)
    tracker._rollover_if_new_day(now=datetime.now(timezone.utc) + timedelta(days=1))
    assert tracker.used_today == 0
    assert tracker.would_exceed(4900) is False


def test_api_usage_tracker_persists_across_instances(tmp_path):
    path = str(tmp_path / "usage.json")
    copy_seller.ApiUsageTracker(storage_path=path).record(123)
    reloaded = copy_seller.ApiUsageTracker(storage_path=path)
    assert reloaded.used_today == 123


# ---------------------------------------------------------------------------
# run_copy_seller orchestration (eBay boundary mocked)
# ---------------------------------------------------------------------------

def _details_for(item_id, sold, days_old=10):
    # Realistic getItem shape: sold quantity lives under estimatedAvailabilities.
    created = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    return {
        "itemId": item_id,
        "title": f"Some Product {item_id}",
        "estimatedAvailabilities": [{"estimatedSoldQuantity": sold}],
        "itemCreationDate": created,
        "itemWebUrl": f"https://www.ebay.com/itm/{item_id}",
        "price": {"value": "9.99", "currency": "USD"},
        "image": {"imageUrl": "https://example.com/img.jpg"},
    }


def test_run_copy_seller_collects_metrics_and_streams_events(monkeypatch, tmp_path):
    seller_items = [_listing("1", 100), _listing("2", 50), _listing("3", 0)]
    # Seller's own listing details (fetched one getItem per listing).
    details = {"1": _details_for("1", 100), "2": _details_for("2", 50)}
    # Competitor detail responses for the top-K demand-coefficient sum. The
    # search returns item ids only (itemSummaries carry no sold quantity); each
    # top-K result is then fetched via getItem as "v1|<id>|0".
    competitor_details = {
        "v1|c1|0": _details_for("c1", 10),
        "v1|c2|0": _details_for("c2", 10),
        "v1|c3|0": _details_for("c3", 10),
    }

    monkeypatch.setattr(copy_seller, "getItemIds", lambda seller: [i["itemId"] for i in seller_items])

    detail_calls = []

    def fake_detail(item_id, verbose=False):
        detail_calls.append(item_id)
        if item_id in details:
            return details[item_id]
        return competitor_details.get(item_id)

    monkeypatch.setattr(copy_seller, "single_get_detailed_item_data", fake_detail)

    search_calls = []

    def fake_search(query, limit=50):
        search_calls.append(query)
        # Realistic itemSummaries: item ids, no estimatedSoldQuantity.
        items = [{"itemId": f"c{i}"} for i in range(1, limit + 1)]
        return {"total_items": 40, "items": items}

    monkeypatch.setattr(copy_seller, "single_search_by_query", fake_search)
    real_tracker_cls = copy_seller.ApiUsageTracker
    monkeypatch.setattr(
        copy_seller, "ApiUsageTracker",
        lambda: real_tracker_cls(storage_path=str(tmp_path / "u.json")),
    )

    events = list(copy_seller.run_copy_seller("someseller", top_n=5, k=3, min_sold=1))

    kinds = [e["type"] for e in events]
    assert kinds[0] == "progress"
    assert kinds[-1] == "result"
    assert "error" not in kinds

    result = events[-1]["data"]
    candidates = result["product_candidates"]
    # item "3" (0 sold) skipped below min_sold; two candidates remain
    assert len(candidates) == 2
    # ordered by sold desc: item 1 first
    assert candidates[0]["listing_url"] == "https://www.ebay.com/itm/1"
    assert candidates[0]["competition_count"] == 40
    # demand coefficient: top-K sold sum (3 detail calls × 10) ÷ active total (40)
    assert candidates[0]["demand_coefficient"] == pytest.approx(30 / 40)
    # sold velocity: 100 sold ÷ 10 days
    assert candidates[0]["sold_velocity"] == pytest.approx(10.0)
    assert candidates[0]["search_phrase"]
    # one phrase search per candidate
    assert len(search_calls) == 2
    # top-K competitor detail calls per candidate (K=3), as v1|<id>|0 getItem ids
    competitor_calls = [c for c in detail_calls if c.startswith("v1|")]
    assert competitor_calls == ["v1|c1|0", "v1|c2|0", "v1|c3|0"] * 2


def test_run_copy_seller_result_has_no_weights(monkeypatch, tmp_path):
    """Ticket 09: the pipeline no longer accepts or emits ranking weights."""
    monkeypatch.setattr(copy_seller, "getItemIds", lambda seller: ["1"])
    monkeypatch.setattr(
        copy_seller,
        "single_get_detailed_item_data",
        lambda item_id, verbose=False: _details_for("1", 100),
    )
    monkeypatch.setattr(
        copy_seller,
        "single_search_by_query",
        lambda query, limit=50: {"total_items": 40, "items": []},
    )
    real_tracker_cls = copy_seller.ApiUsageTracker
    monkeypatch.setattr(
        copy_seller, "ApiUsageTracker",
        lambda: real_tracker_cls(storage_path=str(tmp_path / "u.json")),
    )

    events = list(copy_seller.run_copy_seller(
        "someseller", top_n=5, k=3, min_sold=1, storage_root=str(tmp_path),
    ))
    result = events[-1]["data"]
    assert "weights" not in result

    saved = copy_seller.load_pipeline_run(result["run_id"], storage_root=str(tmp_path))
    assert "weights" not in saved


def test_run_copy_seller_emits_error_when_budget_exceeded(monkeypatch, tmp_path):
    tracker = copy_seller.ApiUsageTracker(storage_path=str(tmp_path / "u.json"), daily_budget=10)
    tracker.record(10)
    monkeypatch.setattr(copy_seller, "ApiUsageTracker", lambda: tracker)

    events = list(copy_seller.run_copy_seller("someseller", top_n=25, k=20, min_sold=1))
    assert events[-1]["type"] == "error"
    assert "budget" in events[-1]["error"].lower()
