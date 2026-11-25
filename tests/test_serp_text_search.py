import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock

import backend.serp as serp_module
from backend.serp import search_by_text, order_by_site_priority
from backend.constants.serp import BLACKLISTED_SITES, QUERY_EXCLUDED_SITES, SITE_TYPE_WHITELISTED


def _mock_google_search(get_dict_return):
    mock_instance = MagicMock()
    mock_instance.get_dict.return_value = get_dict_return
    return mock_instance


SERPAPI_TEXT_RESPONSE = {
    "organic_results": [
        {
            "title": "Benchy - 3D model",
            "link": "https://www.thingiverse.com/thing:763622",
            "snippet": "Download files and build them with your 3D printer.",
        },
        {
            "title": "Benchy on eBay",
            "link": "https://www.ebay.com/itm/123456",
            "snippet": "Buy benchy now.",
        },
        {
            "title": "Random blog",
            "link": "https://example-blog.com/post/1",
            "snippet": "A blog post about benchy.",
        },
        {
            "title": "Benchy on Reddit",
            "link": "https://www.reddit.com/r/3Dprinting/comments/abc/benchy",
            "snippet": "Discussion about benchy.",
        },
        {
            "title": "Dillon tag on Printables",
            "link": "https://www.printables.com/tag/dillon",
            "snippet": "Models tagged dillon.",
        },
        {
            "title": "Benchy model on Printables",
            "link": "https://www.printables.com/model/68734",
            "snippet": "A specific benchy model.",
        },
    ]
}


def test_search_by_text_uses_google_engine_with_query():
    with patch.dict(os.environ, {"serp_api_token": "test-key"}):
        with patch.object(serp_module, "GoogleSearch") as mock_gs:
            mock_gs.return_value = _mock_google_search({"organic_results": []})
            search_by_text("benchy 3d file")
            params = mock_gs.call_args[0][0]
            assert params["engine"] == "google"
            assert params["q"].startswith("benchy 3d file")
            assert params["api_key"] == "test-key"
            assert params["num"] == 35


def test_search_by_text_appends_site_exclusions_for_every_blacklisted_domain():
    with patch.dict(os.environ, {"serp_api_token": "test-key"}):
        with patch.object(serp_module, "GoogleSearch") as mock_gs:
            mock_gs.return_value = _mock_google_search({"organic_results": []})
            search_by_text("benchy 3d file")
            q = mock_gs.call_args[0][0]["q"]
            for domain in BLACKLISTED_SITES:
                assert f"-site:{domain}" in q


def test_search_by_text_excludes_yeggi_from_query():
    with patch.dict(os.environ, {"serp_api_token": "test-key"}):
        with patch.object(serp_module, "GoogleSearch") as mock_gs:
            mock_gs.return_value = _mock_google_search({"organic_results": []})
            search_by_text("benchy 3d file")
            q = mock_gs.call_args[0][0]["q"]
            assert "-site:yeggi.com" in q
            assert "yeggi.com" in QUERY_EXCLUDED_SITES


def test_search_by_text_sends_num_from_max_results():
    with patch.dict(os.environ, {"serp_api_token": "test-key"}):
        with patch.object(serp_module, "GoogleSearch") as mock_gs:
            mock_gs.return_value = _mock_google_search({"organic_results": []})
            search_by_text("benchy 3d file", max_results=10)
            assert mock_gs.call_args[0][0]["num"] == 10


def test_search_by_text_raises_when_api_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("serp_api_token", None)
        try:
            search_by_text("benchy")
            assert False, "expected ValueError"
        except ValueError as e:
            assert "serp_api_token" in str(e)


def test_search_by_text_extracts_and_classifies_organic_results():
    with patch.dict(os.environ, {"serp_api_token": "test-key"}):
        with patch.object(serp_module, "GoogleSearch") as mock_gs:
            mock_gs.return_value = _mock_google_search(SERPAPI_TEXT_RESPONSE)
            results = search_by_text("benchy 3d file")

    assert len(results) == 6
    first = results[0]
    assert first["title"] == "Benchy - 3D model"
    assert first["link"] == "https://www.thingiverse.com/thing:763622"
    assert first["snippet"] == "Download files and build them with your 3D printer."
    assert first["site_type"] == SITE_TYPE_WHITELISTED
    assert results[1]["site_type"] == "blacklisted"
    assert results[2]["site_type"] == "neutral"
    assert results[3]["site_type"] == "blacklisted"  # reddit.com
    assert results[4]["site_type"] == "blacklisted"  # printables tag page, not a product
    assert results[5]["site_type"] == SITE_TYPE_WHITELISTED  # printables /model/ page


def test_classify_site_product_route_validation():
    from backend.serp import _classify_site
    # Valid product pages stay whitelisted
    assert _classify_site("https://www.thingiverse.com/thing:763622") == SITE_TYPE_WHITELISTED
    assert _classify_site("https://www.printables.com/model/68734") == SITE_TYPE_WHITELISTED
    assert _classify_site("https://thangs.com/designer/foo/3d-model/Foo-1412046") == SITE_TYPE_WHITELISTED
    assert _classify_site("https://makerworld.com/en/models/2462393") == SITE_TYPE_WHITELISTED
    assert _classify_site("https://cults3d.com/en/3d-model/tool/benchy") == SITE_TYPE_WHITELISTED
    # Yeggi was removed from the whitelist — its aggregator links are neutral
    assert _classify_site("https://www.yeggi.com/q/benchy/") == "neutral"
    # Whitelisted domains on non-product routes become blacklisted
    assert _classify_site("https://www.printables.com/tag/dillon") == "blacklisted"
    assert _classify_site("https://www.thingiverse.com/tag:benchy") == "blacklisted"
    assert _classify_site("https://makerworld.com/en/search?q=benchy") == "blacklisted"


PRIORITY_LINKS = [
    {"title": "Blog", "link": "https://example-blog.com/post/1", "snippet": "", "site_type": "neutral"},
    {"title": "Thangs", "link": "https://thangs.com/m/1", "snippet": "", "site_type": SITE_TYPE_WHITELISTED},
    {"title": "Printables", "link": "https://www.printables.com/model/2", "snippet": "", "site_type": SITE_TYPE_WHITELISTED},
    {"title": "eBay", "link": "https://www.ebay.com/itm/3", "snippet": "", "site_type": "blacklisted"},
    {"title": "Thingiverse", "link": "https://www.thingiverse.com/thing:4", "snippet": "", "site_type": SITE_TYPE_WHITELISTED},
]


def test_order_by_site_priority_puts_higher_priority_sites_first():
    ordered = order_by_site_priority(PRIORITY_LINKS, ["thingiverse.com", "printables.com", "thangs.com"])
    hosts = [r["link"] for r in ordered]
    assert hosts.index("https://www.thingiverse.com/thing:4") < hosts.index("https://www.printables.com/model/2")
    assert hosts.index("https://www.printables.com/model/2") < hosts.index("https://thangs.com/m/1")


def test_order_by_site_priority_assigns_priority_rank():
    ordered = order_by_site_priority(PRIORITY_LINKS, ["thingiverse.com", "printables.com", "thangs.com"])
    by_link = {r["link"]: r for r in ordered}
    assert by_link["https://www.thingiverse.com/thing:4"]["priority_rank"] == 0
    assert by_link["https://www.printables.com/model/2"]["priority_rank"] == 1
    assert by_link["https://thangs.com/m/1"]["priority_rank"] == 2


def test_order_by_site_priority_unlisted_sites_keep_relative_order_at_end():
    ordered = order_by_site_priority(PRIORITY_LINKS, ["printables.com"])
    assert ordered[0]["link"] == "https://www.printables.com/model/2"
    rest = [r["link"] for r in ordered[1:]]
    assert rest == [
        "https://example-blog.com/post/1",
        "https://thangs.com/m/1",
        "https://www.ebay.com/itm/3",
        "https://www.thingiverse.com/thing:4",
    ]
    assert all(r["priority_rank"] is None for r in ordered[1:])


def test_order_by_site_priority_none_priorities_preserves_order():
    ordered = order_by_site_priority(PRIORITY_LINKS, None)
    assert [r["link"] for r in ordered] == [r["link"] for r in PRIORITY_LINKS]
    assert all(r["priority_rank"] is None for r in ordered)
