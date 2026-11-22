import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.downloaders import cults3d


GALLERY_HTML = """
<html><body>
<div class="slides__slide"><img data-src="https://fbi.cults3d.com/uploaders/123/illustration-file/aaa/img1.jpg" src="thumb1.jpg"></div>
<div class="slides__slide"><img data-src="https://fbi.cults3d.com/uploaders/123/illustration-file/bbb/img2.jpg"></div>
</body></html>
"""


class _FakeSB:
    """Mimics the SeleniumBase SB context manager used by the Cults3D downloader."""
    html = ""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def uc_open_with_reconnect(self, url, reconnect_time):
        pass

    def get_page_source(self):
        return type(self).html


def _use_fake_browser(monkeypatch, html):
    _FakeSB.html = html
    monkeypatch.setattr(cults3d, "_require_seleniumbase", lambda: _FakeSB)
    monkeypatch.setattr(cults3d, "_wait_for_cloudflare", lambda sb, timeout=20: True)
    monkeypatch.setattr(cults3d, "_dismiss_overlays", lambda sb: None)


def test_cults3d_scrape_images_returns_lightbox_originals(monkeypatch):
    _use_fake_browser(monkeypatch, GALLERY_HTML)
    urls = cults3d.scrape_images("https://cults3d.com/en/3d-model/art/some-model")
    assert urls == [
        "https://fbi.cults3d.com/uploaders/123/illustration-file/aaa/img1.jpg",
        "https://fbi.cults3d.com/uploaders/123/illustration-file/bbb/img2.jpg",
    ]


def test_cults3d_scrape_images_dedupes_and_skips_missing_data_src(monkeypatch):
    html = """
    <div class="slides__slide"><img data-src="https://fbi.cults3d.com/a.jpg"></div>
    <div class="slides__slide"><img data-src="https://fbi.cults3d.com/a.jpg"></div>
    <div class="slides__slide"><img src="no-data-src.jpg"></div>
    """
    _use_fake_browser(monkeypatch, html)
    urls = cults3d.scrape_images("https://cults3d.com/en/3d-model/art/some-model")
    assert urls == ["https://fbi.cults3d.com/a.jpg"]


def test_cults3d_scrape_images_raises_on_bad_link():
    try:
        cults3d.scrape_images("https://example.com/no-slug")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a link with no model slug")


def test_cults3d_probe_images_ok_when_images_found(monkeypatch):
    monkeypatch.setattr(cults3d, "scrape_images", lambda link: ["https://fbi.cults3d.com/a.jpg"])
    ok, message = cults3d.probe_images()
    assert ok
    assert "1" in message


def test_cults3d_probe_images_fails_when_no_images(monkeypatch):
    monkeypatch.setattr(cults3d, "scrape_images", lambda link: [])
    ok, _ = cults3d.probe_images()
    assert not ok


def test_cults3d_probe_images_fails_on_error(monkeypatch):
    def boom(link):
        raise RuntimeError("cloudflare blocked")
    monkeypatch.setattr(cults3d, "scrape_images", boom)
    ok, message = cults3d.probe_images()
    assert not ok
    assert "cloudflare blocked" in message
