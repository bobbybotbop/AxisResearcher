"""
Tests for the Saved 3D Files API endpoints (GLOSSARY: "Saved 3D File").

Seam under test: the HTTP surface — GET /api/saved-3d-files (paginated list,
newest first), GET /api/saved-3d-files/<id> (full detail), and
DELETE /api/saved-3d-files/<id> (removes the record and its on-disk file +
site-image directory). The storage layer is routed at a tmp axis.db and the
Saved_3D_Files directory at a tmp path, so tests stay isolated.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module
import backend.db as db
from app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "axis.db"))
    monkeypatch.setattr(app_module, "SAVED_3D_FILES_DIR", str(tmp_path / "Saved_3D_Files"))
    db.init_db()
    return app.test_client()


def _record(**overrides):
    data = {
        "ebay_listing_url": "https://www.ebay.com/itm/197523731100",
        "ebay_listing_title": "Dragon Bookend 3D Printed",
        "source_site": "thingiverse.com",
        "source_url": "https://www.thingiverse.com/thing:3539464",
        "match_label": "confirmed_image_match",
        "pipeline": "image_search",
        "file_path": "Saved_3D_Files/1.zip",
        "images_dir": "Saved_3D_Files/1_images",
    }
    data.update(overrides)
    return data


# --- GET /api/saved-3d-files (list) ---

def test_list_saved_3d_files_empty(client):
    res = client.get("/api/saved-3d-files")
    assert res.status_code == 200
    data = res.get_json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 25


def test_list_saved_3d_files_paginated_newest_first(client):
    ids = [db.save_saved_3d_file(_record(ebay_listing_title=f"Model {i}")) for i in range(3)]
    res = client.get("/api/saved-3d-files?page=1&page_size=2")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total"] == 3
    assert data["page_size"] == 2
    assert [item["id"] for item in data["items"]] == [ids[2], ids[1]]
    res = client.get("/api/saved-3d-files?page=2&page_size=2")
    assert [item["id"] for item in res.get_json()["items"]] == [ids[0]]


# --- GET /api/saved-3d-files/<id> (detail) ---

def test_get_saved_3d_file_detail(client):
    entry_id = db.save_saved_3d_file(_record())
    res = client.get(f"/api/saved-3d-files/{entry_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == entry_id
    assert data["ebay_listing_url"] == "https://www.ebay.com/itm/197523731100"
    assert data["ebay_listing_title"] == "Dragon Bookend 3D Printed"
    assert data["source_site"] == "thingiverse.com"
    assert data["source_url"] == "https://www.thingiverse.com/thing:3539464"
    assert data["match_label"] == "confirmed_image_match"
    assert data["pipeline"] == "image_search"
    assert data["file_path"] == "Saved_3D_Files/1.zip"
    assert data["images_dir"] == "Saved_3D_Files/1_images"
    assert data["created_at"]


def test_get_saved_3d_file_detail_missing_returns_404(client):
    res = client.get("/api/saved-3d-files/9999")
    assert res.status_code == 404


# --- DELETE /api/saved-3d-files/<id> ---

def test_delete_saved_3d_file_removes_record_and_files(client, tmp_path):
    saved_dir = tmp_path / "Saved_3D_Files"
    saved_dir.mkdir()
    file_path = saved_dir / "1.zip"
    file_path.write_bytes(b"zip-bytes")
    images_dir = saved_dir / "1_images"
    images_dir.mkdir()
    (images_dir / "a.jpg").write_bytes(b"jpg-bytes")

    entry_id = db.save_saved_3d_file(_record(
        file_path=str(file_path),
        images_dir=str(images_dir),
    ))
    res = client.delete(f"/api/saved-3d-files/{entry_id}")
    assert res.status_code == 200
    assert res.get_json()["success"] is True
    assert db.get_saved_3d_file(entry_id) is None
    assert not file_path.exists()
    assert not images_dir.exists()


def test_delete_saved_3d_file_missing_returns_404(client):
    res = client.delete("/api/saved-3d-files/9999")
    assert res.status_code == 404
