import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from backend.downloaders import makerworld


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


DESIGN_PAYLOAD = {
    "id": 2462393,
    "title": "Probe Model",
    "coverUrl": "https://makerworld.bblmw.com/cover.jpg?x-oss-process=image/resize,w_400",
    "defaultInstanceId": 111,
    "instances": [
        {
            "id": 111,
            "pictures": [
                "https://makerworld.bblmw.com/pic1.jpg?x-oss-process=image/resize,w_400",
                "https://makerworld.bblmw.com/pic2.jpg",
            ],
        },
        {
            "id": 222,
            "pictures": ["https://makerworld.bblmw.com/other-instance.jpg"],
        },
    ],
}


def test_makerworld_scrape_images_returns_cover_and_default_instance_pictures(monkeypatch):
    monkeypatch.setattr(
        makerworld.requests, "get", lambda *a, **k: _FakeResponse(DESIGN_PAYLOAD)
    )
    urls = makerworld.scrape_images("https://makerworld.com/en/models/2462393")
    assert urls == [
        "https://makerworld.bblmw.com/cover.jpg",
        "https://makerworld.bblmw.com/pic1.jpg",
        "https://makerworld.bblmw.com/pic2.jpg",
    ]


def test_makerworld_scrape_images_strips_oss_params_and_dedupes(monkeypatch):
    payload = {
        "coverUrl": "https://cdn.example.com/same.jpg?x-oss-process=image/resize,w_100",
        "instances": [
            {"id": 1, "pictures": ["https://cdn.example.com/same.jpg", "https://cdn.example.com/other.jpg?x-oss-process=image/resize,w_50"]},
        ],
    }
    monkeypatch.setattr(makerworld.requests, "get", lambda *a, **k: _FakeResponse(payload))
    urls = makerworld.scrape_images("https://makerworld.com/en/models/2462393")
    assert urls == ["https://cdn.example.com/same.jpg", "https://cdn.example.com/other.jpg"]


def test_makerworld_scrape_images_uses_url_instance_id_when_given(monkeypatch):
    monkeypatch.setattr(
        makerworld.requests, "get", lambda *a, **k: _FakeResponse(DESIGN_PAYLOAD)
    )
    urls = makerworld.scrape_images("https://makerworld.com/en/models/2462393#profileId-222")
    assert "https://makerworld.bblmw.com/other-instance.jpg" in urls
    assert "https://makerworld.bblmw.com/pic1.jpg" not in urls


def test_makerworld_scrape_images_raises_on_bad_link():
    try:
        makerworld.scrape_images("https://example.com/no-model")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a link with no model ID")


def test_makerworld_probe_images_ok_when_images_found(monkeypatch):
    monkeypatch.setattr(
        makerworld, "scrape_images", lambda link: ["https://x/a.jpg", "https://x/b.jpg"]
    )
    ok, message = makerworld.probe_images()
    assert ok
    assert "2" in message


def test_makerworld_probe_images_fails_when_no_images(monkeypatch):
    monkeypatch.setattr(makerworld, "scrape_images", lambda link: [])
    ok, _ = makerworld.probe_images()
    assert not ok


def test_makerworld_probe_images_fails_on_error(monkeypatch):
    def boom(link):
        raise RuntimeError("design API down")
    monkeypatch.setattr(makerworld, "scrape_images", boom)
    ok, message = makerworld.probe_images()
    assert not ok
    assert "design API down" in message
