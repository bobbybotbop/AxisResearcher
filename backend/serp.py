import os
from serpapi import GoogleSearch
from urllib.parse import urlparse
from backend.constants.serp import WHITELISTED_SITES, BLACKLISTED_SITES, SITE_TYPE_WHITELISTED


def _extract_host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _classify_site(link: str) -> str:
    try:
        host = _extract_host(link)
        if any(host == s or host.endswith("." + s) for s in WHITELISTED_SITES):
            return SITE_TYPE_WHITELISTED
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


def sort_links_by_priority(links: list[dict], site_priority: list[str] | None) -> list[dict]:
    """Order whitelisted results by the user's site priority (most-preferred first).

    Whitelisted results whose site appears in site_priority are ranked by that
    order; whitelisted results absent from the list and all non-whitelisted
    results keep their original relative order and follow after. None or an
    empty list means no preference — the original order is returned unchanged.
    """
    if not site_priority:
        return links

    def rank(link: dict) -> int:
        host = _extract_host(link["link"])
        for i, s in enumerate(site_priority):
            if host == s or host.endswith("." + s):
                return i
        return len(site_priority)

    whitelisted = [r for r in links if r.get("site_type") == SITE_TYPE_WHITELISTED]
    rest = [r for r in links if r.get("site_type") != SITE_TYPE_WHITELISTED]
    # Python's sort is stable, so unlisted whitelisted sites keep Google rank.
    whitelisted.sort(key=rank)
    return whitelisted + rest


def filter_links_by_enabled_sites(links: list[dict], enabled_sites: list[str] | None) -> list[dict]:
    """Drop whitelisted results whose host is not in enabled_sites.
    None means all sites are enabled (backward-compatible default)."""
    if enabled_sites is None:
        return links
    result = []
    for r in links:
        if r.get("site_type") != SITE_TYPE_WHITELISTED:
            result.append(r)
            continue
        host = _extract_host(r["link"])
        if any(host == s or host.endswith("." + s) for s in enabled_sites):
            result.append(r)
    return result
