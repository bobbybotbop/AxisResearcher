"""
Tests for the SQLite storage foundation (backend/db.py).

Seam under test: the public functions of backend/db.py, exercised against a
tmp axis.db. The database is the single persistent store for structured
application data (GLOSSARY: "SQLite Database") — preferences, listings, logs,
prompts — replacing the JSON files.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.db as db


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "axis.db"
    monkeypatch.setattr(db, "DB_FILE", str(path))
    db.init_db()
    return str(path)


# --- preferences ---

def test_get_preference_missing_returns_default(tmp_db):
    assert db.get_preference("counter", 7) == 7


def test_set_then_get_preference_roundtrip(tmp_db):
    db.set_preference("counter", 42)
    assert db.get_preference("counter") == 42


def test_preferences_preserve_json_types(tmp_db):
    db.set_preference("default_dimensions", {"length": "9", "width": "6", "unit": "INCH"})
    db.set_preference("auto_restock_enabled", True)
    db.set_preference("promoted_listing_ad_rate", 9.5)
    db.set_preference("merchant_location_key", "PlasticLoveShopLocation")
    assert db.get_preference("default_dimensions") == {"length": "9", "width": "6", "unit": "INCH"}
    assert db.get_preference("auto_restock_enabled") is True
    assert db.get_preference("promoted_listing_ad_rate") == 9.5
    assert db.get_preference("merchant_location_key") == "PlasticLoveShopLocation"


def test_set_preference_overwrites(tmp_db):
    db.set_preference("counter", 1)
    db.set_preference("counter", 2)
    assert db.get_preference("counter") == 2


def test_get_all_preferences(tmp_db):
    db.set_preference("a", 1)
    db.set_preference("b", {"x": [1, 2]})
    all_prefs = db.get_all_preferences()
    assert all_prefs == {"a": 1, "b": {"x": [1, 2]}}


# --- listings ---

def _listing(sku="AXIS_1", **overrides):
    data = {
        "sku": sku,
        "ebayListingId": "197523731100",
        "createdDateTime": "2025-07-13T03:59:16.000Z",
        "inventoryItem": {
            "product": {
                "title": f"Title for {sku}",
                "imageUrls": ["https://example.com/a.png", "https://example.com/b.png"],
                "description": "desc",
            },
            "condition": "New",
            "availability": {"shipToLocationAvailability": {"quantity": 15}},
        },
        "offer": {
            "categoryId": "181415",
            "pricingSummary": {"price": {"value": "7.0", "currency": "USD"}},
            "quantity": 15,
        },
    }
    data.update(overrides)
    return data


def test_save_and_load_listing_roundtrip(tmp_db):
    db.save_listing(_listing())
    loaded = db.load_listing("AXIS_1")
    assert loaded == _listing()


def test_load_listing_missing_returns_none(tmp_db):
    assert db.load_listing("NOPE") is None


def test_listing_exists(tmp_db):
    assert db.listing_exists("AXIS_1") is False
    db.save_listing(_listing())
    assert db.listing_exists("AXIS_1") is True


def test_save_listing_updates_in_place(tmp_db):
    db.save_listing(_listing())
    updated = _listing()
    updated["offer"]["quantity"] = 3
    db.save_listing(updated)
    assert db.load_listing("AXIS_1")["offer"]["quantity"] == 3
    assert len(db.list_listings()) == 1


def test_list_listings_returns_all_rows(tmp_db):
    db.save_listing(_listing("AXIS_1"))
    db.save_listing(_listing("AXIS_2"))
    skus = {row["sku"] for row in db.list_listings()}
    assert skus == {"AXIS_1", "AXIS_2"}


def test_list_listings_hidden_flag_preserved_in_raw(tmp_db):
    db.save_listing(_listing("AXIS_1", hidden=True))
    rows = db.list_listings()
    assert rows[0]["hidden"] is True


def test_delete_listing(tmp_db):
    db.save_listing(_listing("AXIS_1"))
    db.save_listing(_listing("AXIS_2"))
    assert db.delete_listing("AXIS_1") is True
    assert db.delete_listing("AXIS_1") is False
    assert [r["sku"] for r in db.list_listings()] == ["AXIS_2"]


def test_save_listing_uses_filename_sku_when_body_sku_missing(tmp_db):
    data = _listing()
    del data["sku"]
    db.save_listing(data, filename="AXIS_9.json")
    assert db.load_listing("AXIS_9") is not None


# --- logs ---

def test_insert_and_read_logs_newest_first(tmp_db):
    db.log("import", "success", count=3)
    db.log("upload", "error", sku="AXIS_1", error="boom")
    logs = db.get_logs()
    assert len(logs) == 2
    assert logs[0]["event"] == "upload"  # newest first
    assert logs[0]["status"] == "error"
    assert logs[0]["sku"] == "AXIS_1"
    assert logs[0]["error"] == "boom"
    assert logs[1]["event"] == "import"
    assert logs[1]["count"] == 3
    assert "timestamp" in logs[0]


def test_logs_auto_trim_to_max_entries(tmp_db, monkeypatch):
    monkeypatch.setattr(db, "MAX_LOG_ENTRIES", 10)
    for i in range(15):
        db.log("evt", "success", i=i)
    logs = db.get_logs()
    assert len(logs) == 10
    # kept the most recent 10 (i=5..14), newest first
    assert logs[0]["i"] == 14
    assert logs[-1]["i"] == 5


def test_insert_log_entry_preserves_given_timestamp(tmp_db):
    db.insert_log_entry({"timestamp": "2026-09-04T02:41:40+00:00", "event": "import",
                         "status": "error", "error": "expired"})
    logs = db.get_logs()
    assert logs[0]["timestamp"] == "2026-09-04T02:41:40+00:00"
    assert logs[0]["error"] == "expired"


# --- prompts ---

def test_save_and_get_prompt_roundtrip(tmp_db):
    db.save_prompt("title/generateTitlePrompt.txt", "Write a title for {original_title}")
    assert db.get_prompt("title/generateTitlePrompt.txt") == "Write a title for {original_title}"


def test_get_prompt_missing_returns_none(tmp_db):
    assert db.get_prompt("title/nope.txt") is None


def test_save_prompt_overwrites_and_stamps_updated_at(tmp_db):
    db.save_prompt("image/experimental.txt", "v1")
    db.save_prompt("image/experimental.txt", "v2")
    assert db.get_prompt("image/experimental.txt") == "v2"


def test_list_prompts_filters_by_type_folder(tmp_db):
    db.save_prompt("title/a.txt", "a")
    db.save_prompt("title/b.txt", "b")
    db.save_prompt("image/c.txt", "c")
    db.save_prompt("categorizeImage.txt", "root")
    assert db.list_prompts("title") == ["a.txt", "b.txt"]
    assert db.list_prompts("image") == ["c.txt"]
    assert db.list_prompts("description") == []


def test_prompt_exists(tmp_db):
    assert db.prompt_exists("title/a.txt") is False
    db.save_prompt("title/a.txt", "a")
    assert db.prompt_exists("title/a.txt") is True


# --- migration ---

@pytest.fixture()
def migration_sources(tmp_path, monkeypatch):
    """A fake project root populated with the four JSON data sources."""
    root = tmp_path / "proj"
    root.mkdir()

    (root / "listingPreferences.json").write_text(json.dumps({
        "counter": 110,
        "merchant_location_key": "PlasticLoveShopLocation",
        "default_quantity": 15,
        "default_dimensions": {"length": "9", "width": "6", "height": "3", "unit": "INCH"},
        "default_weight": {"value": "0.4", "unit": "POUND"},
        "render_profiles": {"layers": {"color": "#0d0d0d"}},
    }), encoding="utf-8")

    gen = root / "Generated_Listings"
    gen.mkdir()
    (gen / "AXIS_1.json").write_text(json.dumps(_listing("AXIS_1")), encoding="utf-8")
    (gen / "AXIS_2.json").write_text(json.dumps(_listing("AXIS_2", hidden=True)), encoding="utf-8")

    (root / "logs.ndjson").write_text(
        '{"timestamp": "2026-09-04T02:41:40+00:00", "event": "import", "status": "error", "error": "expired"}\n'
        '{"timestamp": "2026-09-04T02:42:18+00:00", "event": "draft_created", "status": "success", "sku": "AXIS_85"}\n',
        encoding="utf-8",
    )

    prompts = root / "prompts"
    (prompts / "title").mkdir(parents=True)
    (prompts / "image").mkdir(parents=True)
    (prompts / "title" / "generateTitlePrompt.txt").write_text("title prompt", encoding="utf-8")
    (prompts / "image" / "experimental.txt").write_text("image prompt", encoding="utf-8")
    (prompts / "categorizeImage.txt").write_text("categorize", encoding="utf-8")

    monkeypatch.setattr(db, "PROJECT_ROOT", str(root))
    db_path = tmp_path / "axis.db"
    monkeypatch.setattr(db, "DB_FILE", str(db_path))
    return root


def test_first_run_migrates_all_sources(migration_sources):
    db.ensure_db()  # axis.db did not exist -> migration runs

    assert db.get_preference("counter") == 110
    assert db.get_preference("render_profiles") == {"layers": {"color": "#0d0d0d"}}

    assert db.load_listing("AXIS_1")["sku"] == "AXIS_1"
    assert db.load_listing("AXIS_2")["hidden"] is True

    logs = db.get_logs()
    assert len(logs) == 2
    assert logs[0]["event"] == "draft_created"  # newest first
    assert logs[1]["error"] == "expired"

    assert db.get_prompt("title/generateTitlePrompt.txt") == "title prompt"
    assert db.get_prompt("categorizeImage.txt") == "categorize"
    assert db.list_prompts("image") == ["experimental.txt"]


def test_migration_preserves_source_files(migration_sources):
    db.ensure_db()
    root = migration_sources
    assert (root / "listingPreferences.json").exists()
    assert (root / "Generated_Listings" / "AXIS_1.json").exists()
    assert (root / "logs.ndjson").exists()
    assert (root / "prompts" / "title" / "generateTitlePrompt.txt").exists()


def test_second_run_does_not_reimport(migration_sources):
    db.ensure_db()
    # mutate the DB only; a second ensure_db must not overwrite from JSON
    db.set_preference("counter", 999)
    db.delete_listing("AXIS_1")
    db.ensure_db()
    assert db.get_preference("counter") == 999
    assert db.load_listing("AXIS_1") is None
