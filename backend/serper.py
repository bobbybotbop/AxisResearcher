import os
import requests


def search_by_image(image_url: str) -> dict:
    api_key = os.getenv("serper_api_token")
    if not api_key:
        raise ValueError("serper_api_token is not set in .env")

    payload = {
        "url": image_url,
        "q": "3d file",
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
            if not link:
                continue
            results.append({
                "title": item.get("title", ""),
                "link": link,
                "source": item.get("source", item.get("displayedLink", "")),
                "thumbnail": item.get("thumbnail", ""),
            })

    seen = set()
    unique = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique.append(r)

    return unique[:limit]
