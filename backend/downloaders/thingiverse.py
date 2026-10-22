import io
import re
import time
import zipfile
import cloudscraper

THINGIVERSE_BASE = "https://www.thingiverse.com"

_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

_XHR_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Origin": THINGIVERSE_BASE,
}


def extract_thing_id(link: str) -> str:
    match = re.search(r'thingiverse\.com/thing[:/](\d+)', link)
    if not match:
        raise ValueError(f"No Thingiverse thing ID found in: {link}")
    return match.group(1)


def _make_session() -> cloudscraper.CloudScraper:
    session = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    session.headers.update(_PAGE_HEADERS)
    return session


def _get_files(session: cloudscraper.CloudScraper, thing_id: str) -> list[dict]:
    """Fetch file list via the Thingiverse v2 API. Returns [{"name", "url"}, ...]."""
    referer = f"{THINGIVERSE_BASE}/thing:{thing_id}"

    # Obtain an anonymous VIEW token (no auth required)
    token_r = session.get(
        f"{THINGIVERSE_BASE}/api/v2/auth/view",
        headers={**_XHR_HEADERS, "Referer": referer},
        timeout=15,
    )
    token_r.raise_for_status()
    token = token_r.json()["access"]

    # Fetch complete thing data with the VIEW token
    complete_r = session.get(
        f"{THINGIVERSE_BASE}/api/v2/things/{thing_id}/complete",
        headers={**_XHR_HEADERS, "Authorization": f"Bearer {token}", "Referer": referer},
        timeout=30,
    )
    complete_r.raise_for_status()
    data = complete_r.json()

    zip_files = (data.get("zip_data") or {}).get("files") or []
    return [{"name": f["name"], "url": f["url"]} for f in zip_files if f.get("name") and f.get("url")]


def probe() -> tuple[bool, str]:
    probe_thing_id = "3539464"
    try:
        session = _make_session()
        # Load the main page first so cloudscraper can pass the Cloudflare challenge
        r = session.get(f"{THINGIVERSE_BASE}/thing:{probe_thing_id}", timeout=15)
        r.raise_for_status()
        files = _get_files(session, probe_thing_id)
        if files:
            return True, f"API accessible, {len(files)} file(s) found"
        return False, "API returned no files"
    except Exception as e:
        return False, str(e)


def stream_zip(thing_id: str, file_download_delay: float = 0.0) -> tuple[str, bytes]:
    """Download all files for a Thingiverse thing and return (zip_filename, zip_bytes)."""
    session = _make_session()
    # Load the main page to pass the Cloudflare challenge and acquire session cookies
    r = session.get(f"{THINGIVERSE_BASE}/thing:{thing_id}", timeout=30)
    r.raise_for_status()

    files = _get_files(session, thing_id)
    if not files:
        raise RuntimeError(
            "Could not extract file list from Thingiverse — the API returned no files."
        )

    thing_url = f"{THINGIVERSE_BASE}/thing:{thing_id}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, f in enumerate(files):
            if i > 0 and file_download_delay > 0:
                time.sleep(file_download_delay)
            dr = session.get(f["url"], headers={"Referer": thing_url}, timeout=60)
            dr.raise_for_status()
            zf.writestr(f["name"], dr.content)

    return f"thing_{thing_id}.zip", buf.getvalue()
