import os
import serpapi


def search_by_image(image_url: str) -> dict:
    api_key = os.getenv("serp_api_token")
    if not api_key:
        raise ValueError("serp_api_token is not set in .env")

    client = serpapi.Client(api_key=api_key)
    results = client.search({
        "engine": "google_reverse_image",
        "image_url": image_url,
    })
    return results


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
        })

    seen = set()
    unique = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique.append(r)

    return unique[:limit]
