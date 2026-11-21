"""
Fixture-based tests for POST /api/listings/sync-startup (app.py).

get_seller_list is monkeypatched — no network or eBay credentials are needed.
The listings store is pointed at a tmp axis.db so the real database is never
touched.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.db as db
import app as app_module


def _seller_item(item_id, seller_sku=None, title="T", quantity=3, price="9.99"):
    return {
        "item_id": item_id,
        "seller_sku": seller_sku,
        "title": title,
        "description": "desc",
        "image_urls": ["https://example.com/img.jpg"],
        "condition": "New",
        "quantity": quantity,
        "price": price,
        "start_time": "2026-01-01T00:00:00Z",
    }


def _axis_listing(ebay_listing_id="", ebay_status="active", hidden=False, sku="AXIS_1"):
    data = {
        "sku": sku,
        "ebayListingId": ebay_listing_id,
        "ebay_status": ebay_status,
        "inventoryItem": {
            "product": {"title": "Old", "description": "old", "imageUrls": []},
            "condition": "New",
            "availability": {"shipToLocationAvailability": {"quantity": 1}},
        },
        "offer": {"pricingSummary": {"price": {"value": "1.00"}}, "quantity": 1},
    }
    if hidden:
        data["hidden"] = True
    return data


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the endpoint's listing scan at an isolated tmp axis.db.
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "axis.db"))
    db.init_db()
    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: None)
    # Manual-listing helpers would write to the real listings store; stub them
    # out (the un-hide path under test writes via the DB directly).
    monkeypatch.setattr(app_module, "write_manual_listing_json", lambda item: False)
    monkeypatch.setattr(app_module, "set_listing_ebay_status", lambda sku, status: True)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c.fixture_dir = tmp_path
        yield c


def _write_listing(tmp_path, sku, data):
    db.save_listing(data)


def _read_listing(tmp_path, sku):
    return db.load_listing(sku)


def test_soft_deletes_axis_and_manual_not_in_seller_list(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [_seller_item("333", seller_sku="AXIS_OK")])

    _write_listing(tmp, "AXIS_GONE", _axis_listing(ebay_listing_id="111", sku="AXIS_GONE"))
    manual = _axis_listing(ebay_listing_id="222", sku="MANUAL_222")
    manual["isManualListing"] = True
    _write_listing(tmp, "MANUAL_222", manual)
    _write_listing(tmp, "AXIS_DRAFT", _axis_listing(sku="AXIS_DRAFT"))  # no id, no sku match

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200
    body = res.get_json()
    assert body == {"removed": 2, "healed": 0, "aborted": False}

    gone = _read_listing(tmp, "AXIS_GONE")
    assert gone["hidden"] is True
    assert gone["ebayListingId"] == "111"  # kept so a relist can re-match
    manual_after = _read_listing(tmp, "MANUAL_222")
    assert manual_after["hidden"] is True
    draft = _read_listing(tmp, "AXIS_DRAFT")
    assert "hidden" not in draft


def test_heals_stale_status_and_unhides(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [_seller_item("333", seller_sku="AXIS_BACK", quantity=7)])

    _write_listing(tmp, "AXIS_BACK", _axis_listing(
        ebay_listing_id="333", ebay_status="not_found", hidden=True, sku="AXIS_BACK"))

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200
    body = res.get_json()
    assert body == {"removed": 0, "healed": 1, "aborted": False}

    after = _read_listing(tmp, "AXIS_BACK")
    assert after["ebay_status"] == "active"
    assert "hidden" not in after
    # merge also ran: quantity updated from seller list
    assert after["offer"]["quantity"] == 7


def test_empty_seller_list_aborts_without_changes(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [])
    _write_listing(tmp, "AXIS_GONE", _axis_listing(ebay_listing_id="111", sku="AXIS_GONE"))

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200
    body = res.get_json()
    assert body["aborted"] is True
    assert body["removed"] == 0 and body["healed"] == 0
    assert body["reason"]
    assert "hidden" not in _read_listing(tmp, "AXIS_GONE")


def test_seller_list_error_returns_clean_error_payload(client, monkeypatch):
    tmp = client.fixture_dir

    def _boom():
        raise RuntimeError("token expired")

    monkeypatch.setattr(app_module, "get_seller_list", _boom)
    _write_listing(tmp, "AXIS_GONE", _axis_listing(ebay_listing_id="111", sku="AXIS_GONE"))

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 502
    body = res.get_json()
    assert body["aborted"] is True
    assert "token expired" in body["error"]
    assert body["removed"] == 0 and body["healed"] == 0
    assert "hidden" not in _read_listing(tmp, "AXIS_GONE")


def test_log_payload_includes_sku_lists_and_removed_titles(client, monkeypatch):
    tmp = client.fixture_dir
    captured = []
    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: captured.append((a, k)))
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [
        _seller_item("333", seller_sku="AXIS_BACK", quantity=7),
    ])

    removed_listing = _axis_listing(ebay_listing_id="111", sku="AXIS_GONE")
    removed_listing["inventoryItem"]["product"]["title"] = "Vintage Poster"
    _write_listing(tmp, "AXIS_GONE", removed_listing)
    _write_listing(tmp, "AXIS_BACK", _axis_listing(
        ebay_listing_id="333", ebay_status="not_found", hidden=True, sku="AXIS_BACK"))

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200

    sync_logs = [k for (a, k) in captured if a and a[0] == "sync_startup"]
    assert len(sync_logs) == 1
    payload = sync_logs[0]

    assert payload["removed"] == 1
    assert payload["healed"] == 1
    assert payload["removed_skus"] == ["AXIS_GONE"]
    assert payload["healed_skus"] == ["AXIS_BACK"]
    # Title snapshotted before soft-deletion, from inventoryItem.product.title
    assert payload["removed_titles"] == {"AXIS_GONE": "Vintage Poster"}


def test_log_payload_omits_empty_sku_lists(client, monkeypatch):
    tmp = client.fixture_dir
    captured = []
    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: captured.append((a, k)))
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [
        _seller_item("333", seller_sku="AXIS_OK"),
    ])
    _write_listing(tmp, "AXIS_OK", _axis_listing(ebay_listing_id="333", sku="AXIS_OK"))

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200

    sync_logs = [k for (a, k) in captured if a and a[0] == "sync_startup"]
    assert len(sync_logs) == 1
    payload = sync_logs[0]

    assert payload["removed"] == 0
    assert payload["healed"] == 0
    assert "removed_skus" not in payload
    assert "healed_skus" not in payload
    assert "removed_titles" not in payload


def test_sku_match_heals_missing_ebay_listing_id(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [_seller_item("999", seller_sku="AXIS_SKU")])

    listing = _axis_listing(sku="AXIS_SKU")  # no ebayListingId
    _write_listing(tmp, "AXIS_SKU", listing)

    res = client.post("/api/listings/sync-startup")
    assert res.status_code == 200
    body = res.get_json()
    assert body["removed"] == 0 and body["aborted"] is False
    after = _read_listing(tmp, "AXIS_SKU")
    assert after["ebayListingId"] == "999"
