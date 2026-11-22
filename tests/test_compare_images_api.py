import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io

import pytest
from PIL import Image

import app as app_module
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def _png_bytes(color):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


def _gradient_png_bytes():
    img = Image.new("RGB", (64, 64))
    for x in range(64):
        for y in range(64):
            img.putpixel((x, y), (x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_compare_images_requires_ebay_photos(client):
    res = client.post("/api/compare-images", json={"site_url": "https://www.printables.com/model/68734"})
    assert res.status_code == 400
    assert "ebay_photos" in res.get_json()["error"]


def test_compare_images_requires_site_url(client):
    res = client.post("/api/compare-images", json={"ebay_photos": ["https://i.ebayimg.com/a.jpg"]})
    assert res.status_code == 400
    assert "site_url" in res.get_json()["error"]


def test_compare_images_ebay_photos_must_be_list(client):
    res = client.post(
        "/api/compare-images",
        json={"ebay_photos": "https://i.ebayimg.com/a.jpg", "site_url": "https://www.printables.com/model/68734"},
    )
    assert res.status_code == 400
    assert "ebay_photos" in res.get_json()["error"]


def test_compare_images_match(client, monkeypatch):
    gradient = _gradient_png_bytes()
    monkeypatch.setattr(
        app_module,
        "printables_scrape_images",
        lambda link: ["https://media.printables.com/site.jpg"],
    )
    monkeypatch.setattr(
        app_module,
        "_download_image",
        lambda url, timeout=10: gradient,
    )
    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/ebay.jpg"],
            "site_url": "https://www.printables.com/model/68734",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is True
    assert body["matched_pairs"] == [{"ebay_index": 0, "site_index": 0, "distance": 0}]
    assert body["ebay_image_count"] == 1
    assert body["site_image_count"] == 1


def test_compare_images_no_match(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "printables_scrape_images",
        lambda link: ["https://media.printables.com/site.jpg"],
    )
    downloads = {
        "https://i.ebayimg.com/ebay.jpg": _png_bytes((0, 0, 0)),
        "https://media.printables.com/site.jpg": _gradient_png_bytes(),
    }
    monkeypatch.setattr(
        app_module,
        "_download_image",
        lambda url, timeout=10: downloads[url],
    )
    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/ebay.jpg"],
            "site_url": "https://www.printables.com/model/68734",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is False
    assert body["matched_pairs"] == []
    assert body["ebay_image_count"] == 1
    assert body["site_image_count"] == 1


def test_compare_images_scrape_failure_returns_match_false_with_error(client, monkeypatch):
    def down(link):
        raise RuntimeError("site layout changed")
    monkeypatch.setattr(app_module, "printables_scrape_images", down)
    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/ebay.jpg"],
            "site_url": "https://www.printables.com/model/68734",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is False
    assert "error" in body


def test_compare_images_unsupported_site_returns_match_false_with_error(client):
    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/ebay.jpg"],
            "site_url": "https://example.com/model/1",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is False
    assert "error" in body


def test_compare_images_skips_undownloadable_images(client, monkeypatch):
    gradient = _gradient_png_bytes()
    monkeypatch.setattr(
        app_module,
        "printables_scrape_images",
        lambda link: ["https://media.printables.com/site.jpg"],
    )

    def fake_download(url, timeout=10):
        if "broken" in url:
            raise RuntimeError("404")
        return gradient
    monkeypatch.setattr(app_module, "_download_image", fake_download)

    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/broken.jpg", "https://i.ebayimg.com/ebay.jpg"],
            "site_url": "https://www.printables.com/model/68734",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is True
    # The broken eBay photo was skipped, so the downloaded one is at index 0.
    assert body["matched_pairs"] == [{"ebay_index": 0, "site_index": 0, "distance": 0}]
    assert body["ebay_image_count"] == 1
    assert body["site_image_count"] == 1


def test_compare_images_no_downloadable_images_returns_match_false(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "printables_scrape_images",
        lambda link: ["https://media.printables.com/site.jpg"],
    )

    def fake_download(url, timeout=10):
        raise RuntimeError("404")
    monkeypatch.setattr(app_module, "_download_image", fake_download)

    res = client.post(
        "/api/compare-images",
        json={
            "ebay_photos": ["https://i.ebayimg.com/broken.jpg"],
            "site_url": "https://www.printables.com/model/68734",
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["match"] is False
    assert body["matched_pairs"] == []
    assert body["ebay_image_count"] == 0
    assert body["site_image_count"] == 0
