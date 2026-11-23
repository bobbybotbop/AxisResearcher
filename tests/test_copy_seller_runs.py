"""
Tests for persisting and reloading Copy Seller Pipeline Runs (ticket 06).

Storage seam: save_pipeline_run / list_pipeline_runs / load_pipeline_run in
backend/copy_seller.py, exercised against a tmp_path filesystem — no eBay API.
API seam: GET /api/research/copy-seller/runs and .../runs/<run_id> via the
Flask test client, with the runs storage dir redirected to tmp_path.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module
from app import app
from backend import copy_seller


def _candidate(listing_id, sold=10):
    return {
        "listing_url": f"https://www.ebay.com/itm/{listing_id}",
        "title": f"Some Product {listing_id}",
        "search_phrase": f"product {listing_id}",
        "estimated_sold_quantity": sold,
        "item_creation_date": "2026-11-01T00:00:00.000Z",
        "price": "9.99",
        "currency": "USD",
        "image_url": "https://example.com/img.jpg",
        "demand_coefficient": 1.5,
        "competition_count": 40,
        "sold_velocity": 2.0,
    }


def _run(seller="someseller", candidates=None):
    return {
        "seller": seller,
        "inputs": {"top_n": 25, "k": 20, "min_sold": 1},
        "product_candidates": candidates if candidates is not None else [_candidate("1")],
    }


# ---------------------------------------------------------------------------
# save_pipeline_run
# ---------------------------------------------------------------------------

def test_save_pipeline_run_writes_json_under_seller_runs_dir(tmp_path):
    saved = copy_seller.save_pipeline_run(_run(), storage_root=str(tmp_path))

    assert saved["seller"] == "someseller"
    assert saved["run_id"]
    assert saved["timestamp"]

    path = tmp_path / "someseller" / "runs" / f"{saved['run_id']}.json"
    assert path.exists()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["seller"] == "someseller"
    assert on_disk["inputs"] == {"top_n": 25, "k": 20, "min_sold": 1}
    assert "weights" not in on_disk
    assert on_disk["product_candidates"][0]["listing_url"] == "https://www.ebay.com/itm/1"


def test_save_pipeline_run_sanitizes_seller_for_path(tmp_path):
    saved = copy_seller.save_pipeline_run(_run(seller="some seller/x"), storage_root=str(tmp_path))
    # Path-unsafe characters are replaced, matching ebay_cli's convention.
    assert saved["seller"] == "some seller/x"  # original preserved in the record
    run_files = list(tmp_path.rglob("*.json"))
    assert len(run_files) == 1
    assert "some_seller_x" in str(run_files[0])


# ---------------------------------------------------------------------------
# list_pipeline_runs
# ---------------------------------------------------------------------------

def test_list_pipeline_runs_returns_summaries_newest_first(tmp_path):
    first = copy_seller.save_pipeline_run(_run(seller="alpha"), storage_root=str(tmp_path))
    second = copy_seller.save_pipeline_run(
        _run(seller="beta", candidates=[_candidate("1"), _candidate("2")]),
        storage_root=str(tmp_path),
    )

    summaries = copy_seller.list_pipeline_runs(storage_root=str(tmp_path))

    assert len(summaries) == 2
    # newest first
    assert summaries[0]["run_id"] == second["run_id"]
    assert summaries[1]["run_id"] == first["run_id"]
    # summary shape: seller, timestamp, candidate count — no weights, no candidates
    top = summaries[0]
    assert top["seller"] == "beta"
    assert top["timestamp"] == second["timestamp"]
    assert "weights" not in top
    assert top["candidate_count"] == 2
    assert "product_candidates" not in top


def test_list_pipeline_runs_empty_when_no_runs(tmp_path):
    assert copy_seller.list_pipeline_runs(storage_root=str(tmp_path)) == []


def test_list_pipeline_runs_skips_unparseable_files(tmp_path):
    copy_seller.save_pipeline_run(_run(), storage_root=str(tmp_path))
    bad_dir = tmp_path / "broken" / "runs"
    bad_dir.mkdir(parents=True)
    (bad_dir / "not-a-run.json").write_text("{invalid json", encoding="utf-8")

    summaries = copy_seller.list_pipeline_runs(storage_root=str(tmp_path))
    assert len(summaries) == 1


# ---------------------------------------------------------------------------
# load_pipeline_run
# ---------------------------------------------------------------------------

def test_load_pipeline_run_returns_full_run(tmp_path):
    saved = copy_seller.save_pipeline_run(_run(), storage_root=str(tmp_path))

    loaded = copy_seller.load_pipeline_run(saved["run_id"], storage_root=str(tmp_path))

    assert loaded["run_id"] == saved["run_id"]
    assert loaded["seller"] == "someseller"
    assert loaded["inputs"]["top_n"] == 25
    assert "weights" not in loaded
    assert loaded["product_candidates"][0]["demand_coefficient"] == 1.5


def test_load_pipeline_run_legacy_run_with_weights_still_loads(tmp_path):
    """Ticket 09: legacy saved runs carrying a `weights` field still load;
    the stored weights are ignored (dropped from the returned record)."""
    legacy = _run()
    legacy["weights"] = {"demand": 1.0, "competition": 0.5, "velocity": 2.0}
    saved = copy_seller.save_pipeline_run(legacy, storage_root=str(tmp_path))

    loaded = copy_seller.load_pipeline_run(saved["run_id"], storage_root=str(tmp_path))
    assert loaded is not None
    assert loaded["run_id"] == saved["run_id"]
    assert "weights" not in loaded

    summaries = copy_seller.list_pipeline_runs(storage_root=str(tmp_path))
    assert len(summaries) == 1
    assert "weights" not in summaries[0]


def test_load_pipeline_run_unknown_id_returns_none(tmp_path):
    assert copy_seller.load_pipeline_run("does-not-exist", storage_root=str(tmp_path)) is None


# ---------------------------------------------------------------------------
# run_copy_seller persists the completed run + logs the milestone
# ---------------------------------------------------------------------------

def _stub_ebay_boundary(monkeypatch, tmp_path):
    monkeypatch.setattr(copy_seller, "getItemIds", lambda seller: ["1"])
    monkeypatch.setattr(
        copy_seller,
        "single_get_detailed_item_data",
        lambda item_id, verbose=False: {
            "itemId": item_id,
            "title": "Some Product 1",
            "estimatedSoldQuantity": 100,
            "itemCreationDate": "2026-11-11T00:00:00.000Z",
            "itemWebUrl": "https://www.ebay.com/itm/1",
            "price": {"value": "9.99", "currency": "USD"},
            "image": {"imageUrl": "https://example.com/img.jpg"},
        },
    )
    monkeypatch.setattr(
        copy_seller,
        "single_search_by_query",
        lambda query, limit=50: {"total_items": 40, "items": [{"estimatedSoldQuantity": 10}]},
    )
    real_tracker_cls = copy_seller.ApiUsageTracker
    monkeypatch.setattr(
        copy_seller,
        "ApiUsageTracker",
        lambda: real_tracker_cls(storage_path=str(tmp_path / "usage.json")),
    )


def test_run_copy_seller_saves_run_and_logs_milestone(monkeypatch, tmp_path):
    _stub_ebay_boundary(monkeypatch, tmp_path)
    logged = []
    monkeypatch.setattr(
        copy_seller, "log_event", lambda event, status, **fields: logged.append((event, status, fields))
    )

    events = list(copy_seller.run_copy_seller(
        "someseller", top_n=5, k=3, min_sold=1,
        storage_root=str(tmp_path),
    ))
    assert events[-1]["type"] == "result"

    # Run JSON persisted under <root>/<seller>/runs/
    runs = copy_seller.list_pipeline_runs(storage_root=str(tmp_path))
    assert len(runs) == 1
    assert runs[0]["seller"] == "someseller"
    assert runs[0]["candidate_count"] == 1
    full = copy_seller.load_pipeline_run(runs[0]["run_id"], storage_root=str(tmp_path))
    assert full["inputs"] == {"top_n": 5, "k": 3, "min_sold": 1}
    assert "weights" not in full
    assert full["product_candidates"][0]["listing_url"] == "https://www.ebay.com/itm/1"

    # Milestone logged to logs.ndjson via log_event
    saved_events = [f for e, s, f in logged if e == "copy_seller_run" and s == "saved"]
    assert len(saved_events) == 1
    assert saved_events[0]["seller"] == "someseller"
    assert saved_events[0]["run_id"] == runs[0]["run_id"]


# ---------------------------------------------------------------------------
# API routes: list & fetch past runs
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    return app.test_client()


@pytest.fixture()
def runs_dir(tmp_path, monkeypatch):
    """Redirect Pipeline Run storage to a tmp dir (GENERATED_IMAGES_DIR pattern)."""
    monkeypatch.setattr(copy_seller, "_COLLECTED_DATA_DIR", str(tmp_path))
    return tmp_path


def test_list_runs_endpoint_returns_summaries(client, runs_dir):
    copy_seller.save_pipeline_run(_run(seller="alpha"), storage_root=str(runs_dir))
    copy_seller.save_pipeline_run(_run(seller="beta"), storage_root=str(runs_dir))

    res = client.get("/api/research/copy-seller/runs")
    assert res.status_code == 200
    body = res.get_json()
    assert body["error"] is None
    assert len(body["runs"]) == 2
    sellers = {r["seller"] for r in body["runs"]}
    assert sellers == {"alpha", "beta"}
    for summary in body["runs"]:
        assert summary["run_id"]
        assert summary["timestamp"]
        assert "weights" not in summary
        assert summary["candidate_count"] == 1
        assert "product_candidates" not in summary


def test_list_runs_endpoint_empty(client, runs_dir):
    res = client.get("/api/research/copy-seller/runs")
    assert res.status_code == 200
    assert res.get_json() == {"runs": [], "error": None}


def test_get_run_endpoint_returns_full_run(client, runs_dir):
    saved = copy_seller.save_pipeline_run(_run(), storage_root=str(runs_dir))

    res = client.get(f"/api/research/copy-seller/runs/{saved['run_id']}")
    assert res.status_code == 200
    body = res.get_json()
    assert body["error"] is None
    run = body["run"]
    assert run["run_id"] == saved["run_id"]
    assert run["seller"] == "someseller"
    assert run["inputs"] == {"top_n": 25, "k": 20, "min_sold": 1}
    assert "weights" not in run
    assert run["product_candidates"][0]["listing_url"] == "https://www.ebay.com/itm/1"


def test_get_run_endpoint_unknown_id_404(client, runs_dir):
    res = client.get("/api/research/copy-seller/runs/nope")
    assert res.status_code == 404
    assert res.get_json()["error"]
