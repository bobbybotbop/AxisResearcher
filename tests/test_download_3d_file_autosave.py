"""
Tests for the auto-save behavior of POST /api/download-3d-file (ticket 09).

Seam under test: the HTTP surface of the download endpoint. When the request
carries the pipeline metadata (eBay listing URL/title, pipeline, match label),
a successful download also persists a Saved 3D File (GLOSSARY): the 3D file is
written to Saved_3D_Files/<id>.<ext>, the site images are scraped and stored
in Saved_3D_Files/<id>_images/, and a record is inserted into the database.
Site downloaders/scrapers and image downloads are monkeypatched; the storage
layer is routed at a tmp axis.db and a tmp Saved_3D_Files directory.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module
import backend.db as db
from app import app

THING_URL = "https://www.thingiverse.com/thing:3539464"

METADATA = {
    "ebay_listing_url": "https://www.ebay.com/itm/197523731100",
    "ebay_listing_title": "Dragon Bookend 3D Printed",
    "pipeline": "image_search",
    "match_label": "confirmed_image_match",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_FILE", str(tmp_path / "axis.db"))
    saved_dir = tmp_path / "Saved_3D_Files"
    monkeypatch.setattr(app_module, "SAVED_3D_FILES_DIR", str(saved_dir))
    db.init_db()
    # Fake the Thingiverse download: a small zip payload
    monkeypatch.setattr(
        app_module,
        "tv_stream_zip",
        lambda thing_id, file_download_delay=0.0: ("thing-3539464.zip", b"fake-zip-bytes"),
    )
    # Fake the site image scrape + image downloads
    monkeypatch.setattr(
        app_module,
        "tv_scrape_images",
        lambda link: ["https://cdn.thingiverse.com/a.jpg", "https://cdn.thingiverse.com/b.jpg"],
    )
    monkeypatch.setattr(
        app_module,
        "_download_image",
        lambda url, timeout=10: f"bytes-of-{url.rsplit('/', 1)[-1]}".encode(),
    )
    return app.test_client()


def test_download_without_metadata_does_not_save(client):
    res = client.post("/api/download-3d-file", json={"link": THING_URL})
    assert res.status_code == 200
    assert res.data == b"fake-zip-bytes"
    assert db.list_saved_3d_files()["total"] == 0


def test_download_with_metadata_autosaves_record_file_and_images(client, tmp_path):
    res = client.post("/api/download-3d-file", json={"link": THING_URL, **METADATA})
    assert res.status_code == 200
    # The caller still receives the 3D file bytes
    assert res.data == b"fake-zip-bytes"

    listing = db.list_saved_3d_files()
    assert listing["total"] == 1
    row = listing["items"][0]
    assert row["ebay_listing_url"] == METADATA["ebay_listing_url"]
    assert row["ebay_listing_title"] == METADATA["ebay_listing_title"]
    assert row["pipeline"] == "image_search"
    assert row["match_label"] == "confirmed_image_match"
    assert row["source_site"] == "thingiverse.com"
    assert row["source_url"] == THING_URL
    assert row["created_at"]

    # The 3D file was persisted under Saved_3D_Files/<id>.zip
    saved_dir = tmp_path / "Saved_3D_Files"
    expected_file = saved_dir / f"{row['id']}.zip"
    assert row["file_path"] == str(expected_file)
    assert expected_file.read_bytes() == b"fake-zip-bytes"

    # The site images were downloaded into Saved_3D_Files/<id>_images/
    images_dir = saved_dir / f"{row['id']}_images"
    assert row["images_dir"] == str(images_dir)
    saved_images = sorted(os.listdir(images_dir))
    assert saved_images == ["a.jpg", "b.jpg"]
    assert (images_dir / "a.jpg").read_bytes() == b"bytes-of-a.jpg"


def test_download_autosave_title_search_match_label(client):
    res = client.post(
        "/api/download-3d-file",
        json={
            "link": THING_URL,
            **METADATA,
            "pipeline": "title_search",
            "match_label": "unconfirmed_title_match",
        },
    )
    assert res.status_code == 200
    row = db.list_saved_3d_files()["items"][0]
    assert row["pipeline"] == "title_search"
    assert row["match_label"] == "unconfirmed_title_match"


def test_download_autosave_survives_image_scrape_failure(client, monkeypatch, tmp_path):
    """Site-image persistence is best-effort: a scrape failure must not fail
    the download or the record save (the record keeps an empty images_dir)."""
    def broken_scrape(link):
        raise RuntimeError("site layout changed")
    monkeypatch.setattr(app_module, "tv_scrape_images", broken_scrape)

    res = client.post("/api/download-3d-file", json={"link": THING_URL, **METADATA})
    assert res.status_code == 200
    row = db.list_saved_3d_files()["items"][0]
    assert row["file_path"]
    assert os.path.exists(row["file_path"])
    assert row["images_dir"] == ""


def test_download_autosave_single_file_mode_saves_extracted_file(client, tmp_path):
    """single_file mode persists the extracted model file (not the zip)."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("model.stl", b"stl-bytes")
    zip_bytes = buf.getvalue()

    import app as app_module2
    app_module2.tv_stream_zip = lambda thing_id, file_download_delay=0.0: ("thing.zip", zip_bytes)

    res = client.post(
        "/api/download-3d-file",
        json={"link": THING_URL, "mode": "single_file", **METADATA},
    )
    assert res.status_code == 200
    assert res.data == b"stl-bytes"
    row = db.list_saved_3d_files()["items"][0]
    saved_dir = tmp_path / "Saved_3D_Files"
    expected_file = saved_dir / f"{row['id']}.stl"
    assert row["file_path"] == str(expected_file)
    assert expected_file.read_bytes() == b"stl-bytes"
