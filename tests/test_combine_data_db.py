"""
combine_data persistence seam after the SQLite migration: load_config /
save_config and the listing helpers read/write axis.db instead of
listingPreferences.json / Generated_Listings/*.json.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.db as db
import backend.copyScripts.combine_data as combine_data

BASE_CONFIG = {
    "counter": 1,
    "merchant_location_key": "TestLocation",
    "default_quantity": 1,
    "default_dimensions": {"length": "1", "width": "1", "height": "1", "unit": "INCH"},
    "default_weight": {"value": "1", "unit": "POUND"},
}


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "axis.db"
    monkeypatch.setattr(db, "DB_FILE", str(path))
    db.init_db()
    for key, value in BASE_CONFIG.items():
        db.set_preference(key, value)
    return str(path)


def test_load_config_reads_from_db(tmp_db):
    config = combine_data.load_config()
    assert config["counter"] == 1
    assert config["merchant_location_key"] == "TestLocation"
    assert config["default_dimensions"]["unit"] == "INCH"


def test_load_config_missing_required_key_raises(tmp_db):
    db.set_preference("counter", None)  # present but null still counts as present
    conn_path = db.DB_FILE
    import sqlite3
    with sqlite3.connect(conn_path) as c:
        c.execute("DELETE FROM preferences WHERE key = 'default_weight'")
    with pytest.raises(ValueError, match="missing required keys"):
        combine_data.load_config()


def test_save_config_writes_to_db(tmp_db):
    config = combine_data.load_config()
    config["counter"] = 55
    config["new_key"] = {"nested": [1, 2]}
    combine_data.save_config(config)
    assert db.get_preference("counter") == 55
    assert db.get_preference("new_key") == {"nested": [1, 2]}


def test_get_next_sku_increments_counter_in_db(tmp_db):
    sku = combine_data.get_next_sku()
    assert sku == "AXIS_2"
    assert db.get_preference("counter") == 2


def test_create_and_load_listing_via_db(tmp_db):
    sku = combine_data.create_listing_with_preferences()
    assert combine_data.listing_file_exists(sku)
    loaded = combine_data.load_listing_data(sku=sku)
    assert loaded["sku"] == sku
    # MERCHANT_LOCATION_KEY is a module-level constant frozen at import time.
    assert loaded["offer"]["merchantLocationKey"] == combine_data.MERCHANT_LOCATION_KEY


def test_load_listing_data_missing_returns_none(tmp_db):
    assert combine_data.load_listing_data(sku="AXIS_999") is None


def test_update_local_listing_quantity(tmp_db):
    sku = combine_data.create_listing_with_preferences()
    assert combine_data.update_local_listing_quantity(sku=sku, quantity=7) is True
    assert combine_data.load_listing_data(sku=sku)["offer"]["quantity"] == 7


def test_set_listing_ebay_status(tmp_db):
    sku = combine_data.create_listing_with_preferences()
    assert combine_data.set_listing_ebay_status(sku, "not_found") is True
    assert combine_data.load_listing_data(sku=sku)["ebay_status"] == "not_found"


def test_write_manual_listing_json_insert_and_preserve(tmp_db):
    item = {
        "item_id": "111", "title": "T", "quantity": 5, "price": "9.99",
        "image_urls": ["u"], "condition": "New", "start_time": "2026-01-01",
        "description": "d", "seller_sku": "SELLER1", "is_variation": False,
        "category_id": "181415",
    }
    assert combine_data.write_manual_listing_json(item) is True
    # unchanged rewrite is skipped
    assert combine_data.write_manual_listing_json(item) is False
    # local-only fields survive a changed rewrite
    combine_data.set_listing_ebay_status("SELLER1", "not_found")
    item["quantity"] = 6
    assert combine_data.write_manual_listing_json(item) is True
    loaded = combine_data.load_listing_data(sku="SELLER1")
    assert loaded["offer"]["quantity"] == 6
    assert loaded["ebay_status"] == "not_found"


def test_render_settings_roundtrip_via_db(tmp_db):
    saved = combine_data.save_render_settings(color="#FF0000", resolution=512)
    assert saved["color"] == "#ff0000"
    assert db.get_preference("render_color") == "#ff0000"
    assert combine_data.get_render_settings()["resolution"] == 512
