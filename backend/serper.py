import os
import requests
from urllib.parse import urlparse


INCLUDE_SITES = [
    "makerworld.com",
    "printables.com",
    "yeggi.com",
    "cults3d.com",
    "thingiverse.com",
    "myminifactory.com",
    "thangs.com",
]

EXCLUDE_SITES = [
    "ebay.com",
    "amazon.com",
    "walmart.com",
    "etsy.com",
    "aliexpress.com",
    "temu.com",
    "mercari.com",
    "poshmark.com",
]


def _is_allowed_site(link: str) -> bool:
    try:
        host = urlparse(link).netloc.lower().lstrip("www.")
        return any(host == s or host.endswith("." + s) for s in INCLUDE_SITES)
    except Exception:
        return False


def _build_query():
    parts = ["3d file"]
    for site in EXCLUDE_SITES:
        parts.append(f"-site:{site}")
    site_or = " OR ".join(f"site:{s}" for s in INCLUDE_SITES)
    parts.append(f"({site_or})")
    return " ".join(parts)


def search_by_image(image_url: str) -> dict:
    api_key = os.getenv("serper_api_token")
    if not api_key:
        raise ValueError("serper_api_token is not set in .env")

    payload = {
        "url": image_url,
        "q": _build_query(),
    }

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    resp = requests.post(
        "https://google.serper.dev/lens",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def extract_top_links(serper_response: dict, limit: int = 10) -> list[dict]:
    results = []

    for section_key in ("organic", "knowledgeGraph", "visual_matches", "images"):
        items = serper_response.get(section_key, [])
        if isinstance(items, dict):
            items = [items]
        for item in items:
            link = item.get("link")
            if not link or not _is_allowed_site(link):
                continue
            results.append({
                "title": item.get("title", ""),
                "link": link,
                "source": item.get("source", item.get("displayedLink", "")),
                "thumbnail": item.get("thumbnailUrl") or item.get("imageUrl", ""),
            })

    seen = set()
    unique = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique.append(r)

    return unique[:limit]
