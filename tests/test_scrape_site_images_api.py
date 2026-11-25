import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app as app_module
from app import app


@pytest.fixture()
def client():
    return app.test_client()


def test_scrape_site_images_requires_link(client):
    res = client.post("/api/scrape-site-images", json={})
    assert res.status_code == 400
    assert "link" in res.get_json()["error"]


def test_scrape_site_images_thingiverse(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "tv_scrape_images",
        lambda link: ["https://cdn.thingiverse.com/a.jpg"],
    )
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://www.thingiverse.com/thing:3539464"},
    )
    assert res.status_code == 200
    assert res.get_json()["images"] == ["https://cdn.thingiverse.com/a.jpg"]


def test_scrape_site_images_printables(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "printables_scrape_images",
        lambda link: ["https://media.printables.com/a.jpg"],
    )
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://www.printables.com/model/68734"},
    )
    assert res.status_code == 200
    assert res.get_json()["images"] == ["https://media.printables.com/a.jpg"]


def test_scrape_site_images_makerworld(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "mw_scrape_images",
        lambda link: ["https://makerworld.bblmw.com/a.jpg"],
    )
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://makerworld.com/en/models/2462393"},
    )
    assert res.status_code == 200
    assert res.get_json()["images"] == ["https://makerworld.bblmw.com/a.jpg"]


def test_scrape_site_images_cults3d(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "cults3d_scrape_images",
        lambda link: ["https://fbi.cults3d.com/a.jpg"],
    )
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://cults3d.com/en/3d-model/art/some-model"},
    )
    assert res.status_code == 200
    assert res.get_json()["images"] == ["https://fbi.cults3d.com/a.jpg"]


def test_scrape_site_images_thangs(client, monkeypatch):
    monkeypatch.setattr(
        app_module,
        "thangs_scrape_images",
        lambda link: ["https://thangs.com/a.jpg"],
    )
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://thangs.com/designer/foo/3d-model/Foo-1412046"},
    )
    assert res.status_code == 200
    assert res.get_json()["images"] == ["https://thangs.com/a.jpg"]


def test_scrape_site_images_unsupported_site(client):
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://example.com/model/1"},
    )
    assert res.status_code == 400
    assert "Unsupported site" in res.get_json()["error"]


def test_scrape_site_images_bad_link_returns_400(client, monkeypatch):
    def bad(link):
        raise ValueError("No Thingiverse thing ID found")
    monkeypatch.setattr(app_module, "tv_scrape_images", bad)
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://www.thingiverse.com/nothing-here"},
    )
    assert res.status_code == 400


def test_scrape_site_images_upstream_error_returns_502(client, monkeypatch):
    def down(link):
        raise RuntimeError("site layout changed")
    monkeypatch.setattr(app_module, "printables_scrape_images", down)
    res = client.post(
        "/api/scrape-site-images",
        json={"link": "https://www.printables.com/model/68734"},
    )
    assert res.status_code == 502
