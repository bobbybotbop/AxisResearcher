import json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.downloaders import thangs


def _next_data_page(fallback: dict) -> str:
    page_data = {"props": {"pageProps": {"fallback": fallback}}}
    return (
        '<html><head></head><body>'
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(page_data)}</script>'
        "</body></html>"
    )


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _FakeSession:
    def __init__(self, html):
        self._html = html

    def get(self, url, headers=None, timeout=None):
        return _FakeResponse(self._html)


MODEL_ID = "1412046"
FALLBACK_KEY = f"models/v2/{MODEL_ID}?likes=false"
FALLBACK = {
    FALLBACK_KEY: {
        "attachments": [
            {"imageUrl": "https://thangs.com/img1.jpg"},
            {"imageUrl": "https://thangs.com/img2.jpg"},
        ]
    }
}


def test_thangs_scrape_images_returns_attachment_urls(monkeypatch):
    monkeypatch.setattr(thangs, "_make_session", lambda: _FakeSession(_next_data_page(FALLBACK)))
    urls = thangs.scrape_images(f"https://thangs.com/designer/foo/3d-model/Foo-{MODEL_ID}")
    assert urls == ["https://thangs.com/img1.jpg", "https://thangs.com/img2.jpg"]


def test_thangs_scrape_images_skips_attachments_without_image_url(monkeypatch):
    fallback = {
        FALLBACK_KEY: {
            "attachments": [
                {"imageUrl": "https://thangs.com/a.jpg"},
                {"name": "no-image"},
                {"imageUrl": None},
            ]
        }
    }
    monkeypatch.setattr(thangs, "_make_session", lambda: _FakeSession(_next_data_page(fallback)))
    urls = thangs.scrape_images(f"https://thangs.com/designer/foo/3d-model/Foo-{MODEL_ID}")
    assert urls == ["https://thangs.com/a.jpg"]


def test_thangs_scrape_images_raises_when_fallback_key_missing(monkeypatch):
    monkeypatch.setattr(thangs, "_make_session", lambda: _FakeSession(_next_data_page({})))
    try:
        thangs.scrape_images(f"https://thangs.com/designer/foo/3d-model/Foo-{MODEL_ID}")
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError when the fallback entry is missing")


def test_thangs_scrape_images_raises_on_bad_link():
    try:
        thangs.scrape_images("https://example.com/no-id-here")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a link with no model ID")


def test_thangs_probe_images_ok_when_images_found(monkeypatch):
    monkeypatch.setattr(thangs, "scrape_images", lambda link: ["https://thangs.com/a.jpg"])
    ok, message = thangs.probe_images()
    assert ok
    assert "1" in message


def test_thangs_probe_images_fails_when_no_images(monkeypatch):
    monkeypatch.setattr(thangs, "scrape_images", lambda link: [])
    ok, _ = thangs.probe_images()
    assert not ok


def test_thangs_probe_images_fails_on_error(monkeypatch):
    def boom(link):
        raise RuntimeError("no __NEXT_DATA__")
    monkeypatch.setattr(thangs, "scrape_images", boom)
    ok, message = thangs.probe_images()
    assert not ok
    assert "no __NEXT_DATA__" in message
