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


def make_box_step(tmp_path_factory):
    """Write a 10mm box as a STEP file and return its path. Skips when the
    gmsh native library can't load — it's optional outside the render pipeline."""
    # importorskip only catches ImportError; the gmsh wheel loads its native
    # library at import time and raises ctypes FileNotFoundError when absent.
    try:
        import gmsh
    except Exception as e:
        pytest.skip(f"gmsh native library unavailable: {e}")
    path = tmp_path_factory.mktemp("meshes") / "box.step"
    try:
        gmsh.initialize()
    except Exception as e:
        pytest.skip(f"gmsh native library unavailable: {e}")
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("box")
        gmsh.model.occ.addBox(0, 0, 0, 10, 10, 10)
        gmsh.model.occ.synchronize()
        gmsh.write(str(path))
    finally:
        gmsh.finalize()
    return path
