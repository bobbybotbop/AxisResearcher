import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.serp import sort_links_by_priority
from backend.constants.serp import SITE_TYPE_WHITELISTED

# Ordered as SerpAPI returned them (Google rank), NOT by user priority.
SAMPLE_LINKS = [
    {"link": "https://www.thingiverse.com/thing:789", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://ebay.com/itm/999", "site_type": "blacklisted"},
    {"link": "https://www.printables.com/model/123", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://makerworld.com/en/models/456", "site_type": SITE_TYPE_WHITELISTED},
    {"link": "https://someothersite.com/page", "site_type": "neutral"},
]


def test_none_priority_returns_original_order():
    result = sort_links_by_priority(SAMPLE_LINKS, None)
    assert result == SAMPLE_LINKS


def test_empty_priority_returns_original_order():
    result = sort_links_by_priority(SAMPLE_LINKS, [])
    assert result == SAMPLE_LINKS


def test_whitelisted_results_reordered_by_priority():
    # User prefers printables > makerworld > thingiverse.
    priority = ["printables.com", "makerworld.com", "thingiverse.com"]
    result = sort_links_by_priority(SAMPLE_LINKS, priority)
    links = [r["link"] for r in result]
    assert links == [
        "https://www.printables.com/model/123",
        "https://makerworld.com/en/models/456",
        "https://www.thingiverse.com/thing:789",
        "https://ebay.com/itm/999",
        "https://someothersite.com/page",
    ]


def test_non_whitelisted_keep_relative_order_after_whitelisted():
    priority = ["printables.com", "makerworld.com", "thingiverse.com"]
    result = sort_links_by_priority(SAMPLE_LINKS, priority)
    # Non-whitelisted preserve their original relative order, appended after.
    non_white = [r["link"] for r in result if r["site_type"] != SITE_TYPE_WHITELISTED]
    assert non_white == [
        "https://ebay.com/itm/999",
        "https://someothersite.com/page",
    ]


def test_whitelisted_site_not_in_priority_falls_to_original_relative_order():
    # cults3d is whitelisted but absent from the user's priority list.
    links = [
        {"link": "https://cults3d.com/en/3d-model/1", "site_type": SITE_TYPE_WHITELISTED},
        {"link": "https://www.printables.com/model/123", "site_type": SITE_TYPE_WHITELISTED},
    ]
    priority = ["printables.com"]
    result = sort_links_by_priority(links, priority)
    # printables (in priority) ranks first; cults3d (not listed) keeps its place after.
    assert [r["link"] for r in result] == [
        "https://www.printables.com/model/123",
        "https://cults3d.com/en/3d-model/1",
    ]


def test_subdomain_matches_parent_priority():
    links = [
        {"link": "https://www.thingiverse.com/thing:1", "site_type": SITE_TYPE_WHITELISTED},
        {"link": "https://sub.printables.com/model/9", "site_type": SITE_TYPE_WHITELISTED},
    ]
    priority = ["printables.com", "thingiverse.com"]
    result = sort_links_by_priority(links, priority)
    assert result[0]["link"] == "https://sub.printables.com/model/9"
