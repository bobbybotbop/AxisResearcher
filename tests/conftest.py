"""
Shared fixtures for the test suite.

After the SQLite migration (ticket 01), configuration lives in the preferences
table of axis.db instead of listingPreferences.json. The `config_file` fixture
keeps its historical name but now seeds a throwaway tmp axis.db and points the
storage layer at it, so tests stay isolated from the real database.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import backend.db as db

# Minimal config satisfying load_config()'s required keys
BASE_CONFIG = {
    "counter": 1,
    "merchant_location_key": "TestLocation",
    "default_quantity": 1,
    "default_dimensions": {"length": "1", "width": "1", "height": "1", "unit": "INCH"},
    "default_weight": {"value": "1", "unit": "POUND"},
}


@pytest.fixture()
def config_file(tmp_path, monkeypatch):
    """Seed a tmp axis.db with the minimal valid config and route the storage
    layer at it. Returns the DB path (tests may read preferences back via
    backend.db)."""
    path = tmp_path / "axis.db"
    monkeypatch.setattr(db, "DB_FILE", str(path))
    db.init_db()
    for key, value in BASE_CONFIG.items():
        db.set_preference(key, value)
    return path
