import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app as app_module
from app import app

FAKE_SERP = {
    "image_results": [
        {"title": "t", "link": "https://www.thingiverse.com/thing:789", "source": "s", "thumbnail": ""},
        {"title": "t", "link": "https://www.printables.com/model/123", "source": "s", "thumbnail": ""},
        {"title": "t", "link": "https://makerworld.com/en/models/456", "source": "s", "thumbnail": ""},
    ]
}


@pytest.fixture()
def client():
    return app.test_client()


@pytest.fixture()
def fake_search(monkeypatch):
    monkeypatch.setattr(app_module, "search_by_image", lambda url: FAKE_SERP)


def test_serp_lens_applies_site_priority(client, fake_search):
    res = client.post("/api/serp-lens", json={
        "image_url": "https://example.com/img.jpg",
        "site_priority": ["printables.com", "makerworld.com", "thingiverse.com"],
    })
    assert res.status_code == 200
    links = [r["link"] for r in res.get_json()["results"]]
    assert links == [
        "https://www.printables.com/model/123",
        "https://makerworld.com/en/models/456",
        "https://www.thingiverse.com/thing:789",
    ]


def test_serp_lens_without_priority_keeps_google_order(client, fake_search):
    res = client.post("/api/serp-lens", json={"image_url": "https://example.com/img.jpg"})
    assert res.status_code == 200
    links = [r["link"] for r in res.get_json()["results"]]
    assert links == [
        "https://www.thingiverse.com/thing:789",
        "https://www.printables.com/model/123",
        "https://makerworld.com/en/models/456",
    ]


def test_serp_lens_rejects_non_list_priority(client, fake_search):
    res = client.post("/api/serp-lens", json={
        "image_url": "https://example.com/img.jpg",
        "site_priority": "printables.com",
    })
    assert res.status_code == 400
