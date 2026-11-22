import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import app as app_module
from app import app
from backend.constants.serp import SITE_TYPE_WHITELISTED


@pytest.fixture()
def client():
    return app.test_client()


SEARCH_RESULTS = [
    {"title": "Blog", "link": "https://example-blog.com/post/1", "snippet": "a blog", "site_type": "neutral"},
    {"title": "Thangs", "link": "https://thangs.com/m/1", "snippet": "thangs", "site_type": SITE_TYPE_WHITELISTED},
    {"title": "Printables", "link": "https://www.printables.com/model/2", "snippet": "printables", "site_type": SITE_TYPE_WHITELISTED},
    {"title": "eBay", "link": "https://www.ebay.com/itm/3", "snippet": "ebay", "site_type": "blacklisted"},
    {"title": "Thingiverse", "link": "https://www.thingiverse.com/thing:4", "snippet": "thingiverse", "site_type": SITE_TYPE_WHITELISTED},
]


def test_requires_query(client):
    resp = client.post("/api/serp-text-search", json={})
    assert resp.status_code == 400
    assert "query" in resp.get_json()["error"]


def test_rejects_non_list_enabled_sites(client):
    resp = client.post("/api/serp-text-search", json={"query": "benchy", "enabled_sites": "printables.com"})
    assert resp.status_code == 400
    assert "enabled_sites" in resp.get_json()["error"]


def test_rejects_non_list_site_priorities(client):
    resp = client.post("/api/serp-text-search", json={"query": "benchy", "site_priorities": "printables.com"})
    assert resp.status_code == 400
    assert "site_priorities" in resp.get_json()["error"]


def test_returns_classified_results_with_snippet(client, monkeypatch):
    monkeypatch.setattr(app_module, "search_by_text", lambda query: SEARCH_RESULTS)
    resp = client.post("/api/serp-text-search", json={"query": "benchy 3d file"})
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    first = results[0]
    assert set(first) >= {"title", "link", "snippet", "site_type", "priority_rank"}
    by_link = {r["link"]: r for r in results}
    assert by_link["https://thangs.com/m/1"]["site_type"] == SITE_TYPE_WHITELISTED
    assert by_link["https://example-blog.com/post/1"]["site_type"] == "neutral"


def test_blacklisted_results_are_filtered_from_response(client, monkeypatch):
    monkeypatch.setattr(app_module, "search_by_text", lambda query: SEARCH_RESULTS)
    resp = client.post("/api/serp-text-search", json={"query": "benchy 3d file"})
    assert resp.status_code == 200
    results = resp.get_json()["results"]
    assert all(r["site_type"] != "blacklisted" for r in results)
    assert "https://www.ebay.com/itm/3" not in [r["link"] for r in results]


def test_filters_whitelisted_results_by_enabled_sites(client, monkeypatch):
    monkeypatch.setattr(app_module, "search_by_text", lambda query: SEARCH_RESULTS)
    resp = client.post("/api/serp-text-search", json={
        "query": "benchy",
        "enabled_sites": ["printables.com"],
    })
    links = [r["link"] for r in resp.get_json()["results"]]
    assert "https://www.printables.com/model/2" in links
    assert "https://thangs.com/m/1" not in links
    assert "https://www.thingiverse.com/thing:4" not in links
    # non-whitelisted, non-blacklisted results pass through
    assert "https://example-blog.com/post/1" in links
    # blacklisted results are always dropped
    assert "https://www.ebay.com/itm/3" not in links


def test_orders_by_site_priorities_with_rank(client, monkeypatch):
    monkeypatch.setattr(app_module, "search_by_text", lambda query: SEARCH_RESULTS)
    resp = client.post("/api/serp-text-search", json={
        "query": "benchy",
        "site_priorities": ["thingiverse.com", "printables.com", "thangs.com"],
    })
    results = resp.get_json()["results"]
    links = [r["link"] for r in results]
    assert links.index("https://www.thingiverse.com/thing:4") < links.index("https://www.printables.com/model/2")
    assert links.index("https://www.printables.com/model/2") < links.index("https://thangs.com/m/1")
    by_link = {r["link"]: r for r in results}
    assert by_link["https://www.thingiverse.com/thing:4"]["priority_rank"] == 0
    assert by_link["https://www.printables.com/model/2"]["priority_rank"] == 1
    assert by_link["https://thangs.com/m/1"]["priority_rank"] == 2
    assert by_link["https://example-blog.com/post/1"]["priority_rank"] is None


def test_max_results_is_not_passed_to_search(client, monkeypatch):
    calls = {}

    def fake_search(query):
        calls["query"] = query
        return SEARCH_RESULTS[:2]

    monkeypatch.setattr(app_module, "search_by_text", fake_search)
    resp = client.post("/api/serp-text-search", json={"query": "benchy", "max_results": 5})
    assert resp.status_code == 200
    assert calls == {"query": "benchy"}
    assert len(resp.get_json()["results"]) == 2


def test_missing_api_key_returns_400(client, monkeypatch):
    def fake_search(query):
        raise ValueError("serp_api_token is not set in .env")

    monkeypatch.setattr(app_module, "search_by_text", fake_search)
    resp = client.post("/api/serp-text-search", json={"query": "benchy"})
    assert resp.status_code == 400
    assert "serp_api_token" in resp.get_json()["error"]


def test_unexpected_search_error_returns_500(client, monkeypatch):
    def fake_search(query):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "search_by_text", fake_search)
    resp = client.post("/api/serp-text-search", json={"query": "benchy"})
    assert resp.status_code == 500
    assert "error" in resp.get_json()
