import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.serp import filter_links_by_enabled_sites
from backend.constants.serp import SITE_TYPE_WHITELISTED

SAMPLE_LINKS = [
    {"link": "https://www.printables.com/model/123", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://makerworld.com/en/models/456", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://www.thingiverse.com/thing:789", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://ebay.com/itm/999", "site_type": "blacklisted"},
    {"link": "https://someothersite.com/page", "site_type": "neutral"},
]


def test_none_enabled_sites_returns_all():
    result = filter_links_by_enabled_sites(SAMPLE_LINKS, None)
    assert result == SAMPLE_LINKS


def test_empty_enabled_sites_removes_all_whitelisted():
    result = filter_links_by_enabled_sites(SAMPLE_LINKS, [])
    assert len(result) == 2
    assert all(r["site_type"] != "whitelisted" for r in result)


def test_single_site_keeps_only_that_whitelisted_site():
    result = filter_links_by_enabled_sites(SAMPLE_LINKS, ["printables.com"])
    links = [r["link"] for r in result]
    assert "https://www.printables.com/model/123" in links
    assert "https://makerworld.com/en/models/456" not in links
    assert "https://www.thingiverse.com/thing:789" not in links
    # non-whitelisted results always pass through
    assert "https://ebay.com/itm/999" in links
    assert "https://someothersite.com/page" in links


def test_all_sites_enabled_returns_all():
    all_sites = ["printables.com", "makerworld.com", "thingiverse.com"]
    result = filter_links_by_enabled_sites(SAMPLE_LINKS, all_sites)
    assert result == SAMPLE_LINKS


def test_subdomain_site_is_kept_when_parent_enabled():
    links = [
        {"link": "https://sub.printables.com/model/999", "site_type": SITE_TYPE_WHITELISTED},
    ]
    result = filter_links_by_enabled_sites(links, ["printables.com"])
    assert len(result) == 1
    assert result[0]["link"] == "https://sub.printables.com/model/999"
