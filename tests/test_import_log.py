"""
Fixture-based tests for the import log payload (POST /api/import-listings).

The import log row must distinguish new imports from updates: the logged
payload records imported_count / updated_count and both SKU lists instead of
a single conflated count.

All eBay network calls and listing-file helpers are monkeypatched — no network
or eBay credentials are needed. log_event is replaced with a capture stub so we
assert exactly what gets written to the activity log.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.db as db
import app as app_module


def _item(item_id, seller_sku):
    return {
        "item_id": item_id,
        "title": f"Item {item_id}",
        "quantity": 5,
        "price": "9.99",
        "image_urls": [],
        "condition": "New",
        "start_time": "2026-01-01T00:00:00.000Z",
        "description": "",
        "seller_sku": seller_sku,
        "is_variation": False,
        "category_id": "181415",
    }


@pytest.fixture()
def client(monkeypatch, tmp_path):
    captured = []

    monkeypatch.setattr(app_module, "log_event", lambda *a, **k: captured.append((a, k)))
    monkeypatch.setattr(app_module, "get_manual_import_last_refreshed", lambda: None)
    monkeypatch.setattr(app_module, "save_manual_import_last_refreshed", lambda ts: None)
    # Point the listings store at an empty tmp axis.db so no real rows are read.
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "axis.db"))
    db.init_db()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c.captured_logs = captured
        yield c


def test_import_log_splits_imported_and_updated(client, monkeypatch):
    # Three items from eBay: one brand-new, one already known locally (an
    # existing manual listing), one already an AXIS listing (skipped).
    items = [
        _item("EBAY_NEW", "SKU_NEW"),
        _item("EBAY_EXISTING", "SKU_EXISTING"),
        _item("EBAY_AXIS", "SKU_AXIS"),
    ]
    monkeypatch.setattr(app_module, "get_seller_list", lambda mod_time_from=None: items)

    # EBAY_AXIS is an AXIS listing -> skipped. EBAY_EXISTING is a known manual
    # listing -> updated. EBAY_NEW is unknown -> imported.
    monkeypatch.setattr(app_module, "write_manual_listing_json", lambda item: True)

    # Seed the local-listing index: one manual row (existing) and one axis row.
    db.save_listing({"sku": "SKU_EXISTING", "ebayListingId": "EBAY_EXISTING", "isManualListing": True})
    db.save_listing({"sku": "SKU_AXIS", "ebayListingId": "EBAY_AXIS"})

    res = client.post("/api/import-listings")
    assert res.status_code == 200
    body = res.get_json()
    assert body == {"imported": 1, "updated": 1, "skipped": 1}

    import_logs = [k for (a, k) in client.captured_logs if a and a[0] == "import"]
    assert len(import_logs) == 1
    payload = import_logs[0]

    assert payload["imported_count"] == 1
    assert payload["updated_count"] == 1
    assert payload["imported_skus"] == ["SKU_NEW"]
    assert payload["updated_skus"] == ["SKU_EXISTING"]
