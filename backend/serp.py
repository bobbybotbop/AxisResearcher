import os
from serpapi import GoogleSearch
from urllib.parse import urlparse


WHITELISTED_SITES = [
    "makerworld.com",
    "printables.com",
    "yeggi.com",
    "cults3d.com",
    "thingiverse.com",
    "myminifactory.com",
    "thangs.com",
]

BLACKLISTED_SITES = [
    "ebay.com",
    "amazon.com",
    "walmart.com",
    "etsy.com",
    "aliexpress.com",
    "temu.com",
    "mercari.com",
    "poshmark.com",
]


def _classify_site(link: str) -> str:
    try:
        host = urlparse(link).netloc.lower().removeprefix("www.")
        if any(host == s or host.endswith("." + s) for s in WHITELISTED_SITES):
            return "whitelisted"
        if any(host == s or host.endswith("." + s) for s in BLACKLISTED_SITES):
            return "blacklisted"
    except Exception:
        pass
    return "neutral"


def search_by_image(image_url: str) -> dict:
    api_key = os.getenv("serp_api_token")
    if not api_key:
        raise ValueError("serp_api_token is not set in .env")

    search = GoogleSearch({
        "engine": "google_reverse_image",
        "image_url": image_url,
        "api_key": api_key,
    })
    return search.get_dict()


def extract_top_links(serpapi_response: dict, limit: int = 10) -> list[dict]:
    results = []

    image_results = serpapi_response.get("image_results", [])
    for item in image_results:
        link = item.get("link")
        if not link:
            continue
        results.append({
            "title": item.get("title", ""),
            "link": link,
            "source": item.get("source", ""),
            "thumbnail": item.get("thumbnail", ""),
            "site_type": _classify_site(link),
        })

    seen = set()
    unique = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique.append(r)

    return unique[:limit]
