"""
Fixture-based tests for the sync_active log payload (POST /api/listings/sync-active).

get_seller_list is monkeypatched — no network or eBay credentials are needed.
The listings store is pointed at a tmp axis.db so the real database is never
touched. log_event is replaced with a capture stub so we assert exactly what
gets written to the activity log.
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


def _axis_listing(ebay_listing_id="", ebay_status="active", sku="AXIS_1",
                  title="Old", quantity=1, price="1.00"):
    # Field values mirror _seller_item's defaults so a listing built with the
    # same title/quantity/price merges cleanly (data_changed == False).
    return {
        "sku": sku,
        "ebayListingId": ebay_listing_id,
        "ebay_status": ebay_status,
        "inventoryItem": {
            "product": {
                "title": title,
                "description": "desc",
                "imageUrls": ["https://example.com/img.jpg"],
            },
            "condition": "New",
            "availability": {"shipToLocationAvailability": {"quantity": quantity}},
        },
        "offer": {"pricingSummary": {"price": {"value": price}}, "quantity": quantity},
    }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    captured = []

    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "axis.db"))
    db.init_db()
    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: captured.append((a, k)))
    monkeypatch.setattr(app_module, "write_manual_listing_json", lambda item: False)
    monkeypatch.setattr(app_module, "set_listing_ebay_status", lambda sku, status: True)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c.captured_logs = captured
        c.fixture_dir = tmp_path
        yield c


def _write_listing(tmp_path, sku, data):
    db.save_listing(data)


def _sync_active_payload(client):
    logs = [k for (a, k) in client.captured_logs if a and a[0] == "sync_active"]
    assert len(logs) == 1
    return logs[0]


def test_sync_active_log_includes_sku_lists(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [
        # Matches AXIS_SAME with identical data -> active, not updated.
        _seller_item("111", title="Same", quantity=5, price="2.00"),
        # Matches AXIS_CHANGED but with a different title -> updated.
        _seller_item("222", title="New Title", quantity=5, price="2.00"),
    ])

    _write_listing(tmp, "AXIS_SAME", _axis_listing(
        ebay_listing_id="111", sku="AXIS_SAME",
        title="Same", quantity=5, price="2.00"))
    _write_listing(tmp, "AXIS_CHANGED", _axis_listing(
        ebay_listing_id="222", sku="AXIS_CHANGED",
        title="Old Title", quantity=5, price="2.00"))
    # Has an eBay ID but no match in the seller list -> newly inactive.
    _write_listing(tmp, "AXIS_GONE", _axis_listing(
        ebay_listing_id="999", sku="AXIS_GONE"))

    res = client.post("/api/listings/sync-active")
    assert res.status_code == 200

    payload = _sync_active_payload(client)
    assert payload["active"] == 2
    assert payload["newly_inactive"] == 1
    assert payload["updated"] == 1
    assert payload["newly_inactive_skus"] == ["AXIS_GONE"]
    assert payload["updated_skus"] == ["AXIS_CHANGED"]


def test_sync_active_log_omits_empty_sku_lists(client, monkeypatch):
    tmp = client.fixture_dir
    monkeypatch.setattr(app_module, "get_seller_list", lambda: [
        _seller_item("111", title="Same", quantity=5, price="2.00"),
    ])
    _write_listing(tmp, "AXIS_SAME", _axis_listing(
        ebay_listing_id="111", sku="AXIS_SAME",
        title="Same", quantity=5, price="2.00"))

    res = client.post("/api/listings/sync-active")
    assert res.status_code == 200

    payload = _sync_active_payload(client)
    assert payload["active"] == 1
    assert payload["newly_inactive"] == 0
    assert payload["updated"] == 0
    assert "newly_inactive_skus" not in payload
    assert "updated_skus" not in payload
