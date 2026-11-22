import json
import os
from serpapi import GoogleSearch
from urllib.parse import urlparse
from backend.constants.serp import (
    WHITELISTED_SITES,
    BLACKLISTED_SITES,
    SITE_TYPE_WHITELISTED,
    SITE_TYPE_BLACKLISTED,
    SITE_TYPE_NEUTRAL,
)
from backend.downloaders.thingiverse import extract_thing_id
from backend.downloaders.printables import extract_model_id as printables_model_id
from backend.downloaders.thangs import extract_model_id as thangs_model_id
from backend.downloaders.makerworld import extract_model_info as mw_model_info
from backend.downloaders.cults3d import extract_slug as cults3d_slug

# Per-site validators for whether a whitelisted link points to a specific
# product page (parseable by the site's downloader) rather than a tag/search/
# listing page. Yeggi is an aggregator with no downloader — always accepted.
_PRODUCT_ROUTE_VALIDATORS = {
    "thingiverse.com": extract_thing_id,
    "printables.com": printables_model_id,
    "thangs.com": thangs_model_id,
    "makerworld.com": mw_model_info,
    "cults3d.com": cults3d_slug,
}


def _extract_host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _matches_site(host: str, site: str) -> bool:
    return host == site or host.endswith("." + site)


def _classify_site(link: str) -> str:
    try:
        host = _extract_host(link)
        for site in WHITELISTED_SITES:
            if _matches_site(host, site):
                validator = _PRODUCT_ROUTE_VALIDATORS.get(site)
                if validator is None:
                    return SITE_TYPE_WHITELISTED
                try:
                    validator(link)
                    return SITE_TYPE_WHITELISTED
                except ValueError:
                    # Whitelisted domain but not a specific product page
                    # (tag/search/listing) — treat as blacklisted so it is
                    # excluded from results.
                    return SITE_TYPE_BLACKLISTED
        if any(_matches_site(host, s) for s in BLACKLISTED_SITES):
            return SITE_TYPE_BLACKLISTED
    except Exception:
        pass
    return SITE_TYPE_NEUTRAL


def search_by_text(query: str, max_results: int = 35) -> list[dict]:
    api_key = os.getenv("serp_api_token")
    if not api_key:
        raise ValueError("serp_api_token is not set in .env")

    exclusions = " ".join(f"-site:{domain}" for domain in BLACKLISTED_SITES)
    search = GoogleSearch({
        "engine": "google",
        "q": f"{query} {exclusions}",
        "num": max_results,
        "api_key": api_key,
    })
    raw = search.get_dict()

    results = []
    seen = set()
    for item in raw.get("organic_results", []):
        link = item.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        results.append({
            "title": item.get("title", ""),
            "link": link,
            "snippet": item.get("snippet", ""),
            "site_type": _classify_site(link),
        })
        if len(results) >= max_results:
            break

    print(f"[serp-text-search] query={query!r} — all {len(results)} results (pre-filter):")
    print(json.dumps(results, indent=2))

    return results


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

    print(f"[serp-image-search] all {len(unique)} results (pre-filter, pre-limit):")
    print(json.dumps(unique, indent=2))

    return unique[:limit]


def order_by_site_priority(links: list[dict], site_priorities: list[str] | None) -> list[dict]:
    """Order results so links from higher-priority sites come first.

    site_priorities is a list of domains in priority order (index 0 = highest).
    Each result gets a priority_rank: the site's index in site_priorities, or
    None when the site is unlisted. Unlisted sites keep their relative order
    after all prioritized results. None site_priorities preserves input order."""
    if site_priorities is None:
        return [{**r, "priority_rank": None} for r in links]

    def rank_of(link: str) -> int | None:
        host = _extract_host(link)
        for i, site in enumerate(site_priorities):
            if host == site or host.endswith("." + site):
                return i
        return None

    ranked = [(rank_of(r["link"]), idx, r) for idx, r in enumerate(links)]
    ranked.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else t[1]))
    return [{**r, "priority_rank": rank} for rank, _, r in ranked]


def drop_blacklisted(links: list[dict]) -> list[dict]:
    """Drop results classified as blacklisted (marketplaces, Reddit)."""
    return [r for r in links if r.get("site_type") != SITE_TYPE_BLACKLISTED]


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
