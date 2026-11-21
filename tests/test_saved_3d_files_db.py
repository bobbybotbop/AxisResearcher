"""
Tests for the saved_3d_files table in the SQLite database (backend/db.py).

Seam under test: the public saved-3d-file functions of backend/db.py,
exercised against a tmp axis.db. A Saved 3D File (GLOSSARY) is the persisted
record of a downloaded 3D file: the on-disk file path, the local site-image
directory, the eBay listing URL (photos are never stored), the match label,
and the pipeline that produced it.
"""
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


def test_save_then_get_saved_3d_file_roundtrip(tmp_db):
    new_id = db.save_saved_3d_file(_record())
    assert isinstance(new_id, int)
    row = db.get_saved_3d_file(new_id)
    assert row is not None
    assert row["id"] == new_id
    assert row["ebay_listing_url"] == "https://www.ebay.com/itm/197523731100"
    assert row["ebay_listing_title"] == "Dragon Bookend 3D Printed"
    assert row["source_site"] == "thingiverse.com"
    assert row["source_url"] == "https://www.thingiverse.com/thing:3539464"
    assert row["match_label"] == "confirmed_image_match"
    assert row["pipeline"] == "image_search"
    assert row["file_path"] == "Saved_3D_Files/1.zip"
    assert row["images_dir"] == "Saved_3D_Files/1_images"
    assert row["created_at"]  # ISO timestamp was stamped


def test_get_saved_3d_file_missing_returns_none(tmp_db):
    assert db.get_saved_3d_file(9999) is None


def test_list_saved_3d_files_newest_first_paginated(tmp_db):
    ids = [db.save_saved_3d_file(_record(ebay_listing_title=f"Model {i}")) for i in range(5)]
    page1 = db.list_saved_3d_files(page=1, page_size=2)
    assert page1["total"] == 5
    assert page1["page"] == 1
    assert page1["page_size"] == 2
    assert [r["id"] for r in page1["items"]] == [ids[4], ids[3]]
    page3 = db.list_saved_3d_files(page=3, page_size=2)
    assert [r["id"] for r in page3["items"]] == [ids[0]]
    assert db.list_saved_3d_files(page=4, page_size=2)["items"] == []


def test_delete_saved_3d_file(tmp_db):
    entry_id = db.save_saved_3d_file(_record())
    assert db.delete_saved_3d_file(entry_id) is True
    assert db.get_saved_3d_file(entry_id) is None
    assert db.delete_saved_3d_file(entry_id) is False
