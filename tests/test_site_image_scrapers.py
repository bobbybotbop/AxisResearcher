import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.downloaders import thingiverse, printables


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """Mimics the cloudscraper session used by the Thingiverse downloader."""
    def __init__(self, complete_payload):
        self.headers = {}
        self._complete_payload = complete_payload

    def get(self, url, headers=None, timeout=None):
        if "/api/v2/auth/view" in url:
            return _FakeResponse({"access": "fake-token"})
        if "/api/v2/things/" in url and url.endswith("/complete"):
            return _FakeResponse(self._complete_payload)
        # Main page load (Cloudflare challenge pass)
        return _FakeResponse({}, 200)


COMPLETE_PAYLOAD = {
    "images": [
        {"url": "https://cdn.thingiverse.com/renders/aa/bb/img1.jpg"},
        {"url": "https://cdn.thingiverse.com/renders/cc/dd/img2.jpg"},
    ],
    "zip_data": {"files": []},
}


def test_thingiverse_scrape_images_returns_gallery_urls(monkeypatch):
    monkeypatch.setattr(
        thingiverse, "_make_session", lambda: _FakeSession(COMPLETE_PAYLOAD)
    )
    urls = thingiverse.scrape_images("https://www.thingiverse.com/thing:3539464")
    assert urls == [
        "https://cdn.thingiverse.com/renders/aa/bb/img1.jpg",
        "https://cdn.thingiverse.com/renders/cc/dd/img2.jpg",
    ]


def test_thingiverse_scrape_images_skips_entries_without_url(monkeypatch):
    payload = {"images": [{"url": "https://cdn.thingiverse.com/a.jpg"}, {"name": "no-url"}, {}]}
    monkeypatch.setattr(thingiverse, "_make_session", lambda: _FakeSession(payload))
    urls = thingiverse.scrape_images("https://www.thingiverse.com/thing:3539464")
    assert urls == ["https://cdn.thingiverse.com/a.jpg"]


def test_thingiverse_scrape_images_raises_on_bad_link():
    try:
        thingiverse.scrape_images("https://example.com/not-a-thing")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a link with no thing ID")


def test_thingiverse_probe_images_ok_when_images_found(monkeypatch):
    monkeypatch.setattr(
        thingiverse,
        "scrape_images",
        lambda link: ["https://cdn.thingiverse.com/a.jpg", "https://cdn.thingiverse.com/b.jpg"],
    )
    ok, message = thingiverse.probe_images()
    assert ok
    assert "2" in message


def test_thingiverse_probe_images_fails_when_no_images(monkeypatch):
    monkeypatch.setattr(thingiverse, "scrape_images", lambda link: [])
    ok, _ = thingiverse.probe_images()
    assert not ok


def test_thingiverse_probe_images_fails_on_error(monkeypatch):
    def boom(link):
        raise RuntimeError("cloudflare blocked")
    monkeypatch.setattr(thingiverse, "scrape_images", boom)
    ok, message = thingiverse.probe_images()
    assert not ok
    assert "cloudflare blocked" in message


# --- Printables ---------------------------------------------------------------


def test_printables_scrape_images_returns_media_urls(monkeypatch):
    def fake_gql(query, variables):
        return {
            "print": {
                "images": [
                    {"filePath": "uploads/aa/bb/img1.jpg"},
                    {"filePath": "uploads/cc/dd/img2.png"},
                ]
            }
        }
    monkeypatch.setattr(printables, "_gql", fake_gql)
    urls = printables.scrape_images("https://www.printables.com/model/68734")
    assert urls == [
        "https://media.printables.com/uploads/aa/bb/img1.jpg",
        "https://media.printables.com/uploads/cc/dd/img2.png",
    ]


def test_printables_scrape_images_skips_entries_without_filepath(monkeypatch):
    def fake_gql(query, variables):
        return {"print": {"images": [{"filePath": "uploads/a.jpg"}, {}, {"filePath": None}]}}
    monkeypatch.setattr(printables, "_gql", fake_gql)
    urls = printables.scrape_images("https://www.printables.com/model/68734")
    assert urls == ["https://media.printables.com/uploads/a.jpg"]


def test_printables_scrape_images_raises_for_missing_model(monkeypatch):
    monkeypatch.setattr(printables, "_gql", lambda q, v: {"print": None})
    try:
        printables.scrape_images("https://www.printables.com/model/99999999")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a missing model")


def test_printables_scrape_images_raises_on_bad_link():
    try:
        printables.scrape_images("https://example.com/no-model-id")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a link with no model ID")


def test_printables_probe_images_ok_when_images_found(monkeypatch):
    monkeypatch.setattr(
        printables,
        "scrape_images",
        lambda link: ["https://media.printables.com/a.jpg"],
    )
    ok, message = printables.probe_images()
    assert ok
    assert "1" in message


def test_printables_probe_images_fails_when_no_images(monkeypatch):
    monkeypatch.setattr(printables, "scrape_images", lambda link: [])
    ok, _ = printables.probe_images()
    assert not ok


def test_printables_probe_images_fails_on_error(monkeypatch):
    def boom(link):
        raise RuntimeError("GraphQL errors: boom")
    monkeypatch.setattr(printables, "scrape_images", boom)
    ok, message = printables.probe_images()
    assert not ok
    assert "boom" in message
