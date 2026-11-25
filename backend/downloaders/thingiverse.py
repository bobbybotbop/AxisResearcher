import html as html_lib
import io
import os
import re
import threading
import time
import zipfile
import cloudscraper

try:
    from .browser_reaper import BROWSER_SESSION_LOCK, is_browser_death, reap_stale_profile_chromes
except ImportError:
    from browser_reaper import BROWSER_SESSION_LOCK, is_browser_death, reap_stale_profile_chromes

THINGIVERSE_BASE = "https://www.thingiverse.com"

# Persistent Chrome profile for the browser-based gallery scrape — carries
# Cloudflare clearance between runs. Gitignored.
_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thingiverse_profile")

# A single Chrome profile cannot be shared between concurrent browser
# instances, so serialize browser runs process-wide.
_PROFILE_LOCK = threading.Lock()

# No "br" (brotli): responses arrive undecoded when the brotli package is
# missing, which silently breaks HTML parsing.
_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
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
    "Accept-Encoding": "gzip, deflate",
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


def _require_seleniumbase():
    try:
        from seleniumbase import SB
        return SB
    except ImportError as exc:
        raise RuntimeError(
            "seleniumbase is not installed. Run: pip install seleniumbase"
        ) from exc


def _scrape_images_api(link: str) -> list[str]:
    """Fast path: the v2 `complete` API. It no longer returns the full gallery
    (`images` is gone) — only `default_image`, the primary gallery image."""
    thing_id = extract_thing_id(link)
    session = _make_session()
    # Load the main page first so cloudscraper can pass the Cloudflare challenge
    r = session.get(f"{THINGIVERSE_BASE}/thing:{thing_id}", timeout=15)
    r.raise_for_status()

    referer = f"{THINGIVERSE_BASE}/thing:{thing_id}"
    token_r = session.get(
        f"{THINGIVERSE_BASE}/api/v2/auth/view",
        headers={**_XHR_HEADERS, "Referer": referer},
        timeout=15,
    )
    token_r.raise_for_status()
    token = token_r.json()["access"]

    complete_r = session.get(
        f"{THINGIVERSE_BASE}/api/v2/things/{thing_id}/complete",
        headers={**_XHR_HEADERS, "Authorization": f"Bearer {token}", "Referer": referer},
        timeout=30,
    )
    complete_r.raise_for_status()
    data = complete_r.json()

    urls = [img["url"] for img in (data.get("images") or []) if img.get("url")]
    if not urls:
        default_url = (data.get("default_image") or {}).get("url")
        if default_url:
            urls = [default_url]
    return urls


def _unwrap_resize_url(src: str) -> str | None:
    """Carousel <img> srcs are resize.thingiverse.com wrappers around the
    original cdn.thingiverse.com asset. Return the original, or None for
    non-asset sources."""
    src = html_lib.unescape(src)
    if "resize.thingiverse.com" in src and "url=" in src:
        inner = src.split("url=", 1)[1].split("&", 1)[0]
        if "cdn.thingiverse.com" in inner:
            return inner
        return None
    if "cdn.thingiverse.com" in src:
        return src
    return None


def _scrape_images_browser(link: str) -> list[str]:
    """Full gallery from the hydrated SPA. The Next.js page ships only the
    primary image server-side; the gallery is a carousel (div.carousel-root)
    whose slides lazy-load as you page through, so this clicks "next" and
    collects each slide's img as it appears. Slides carry both user photos
    (assets/) and 3D renders (renders/) — both are gallery images."""
    extract_thing_id(link)  # validate the URL before launching a browser
    SB = _require_seleniumbase()

    urls: list[str] = []
    seen_ids: set[str] = set()

    def collect(page_html: str) -> int:
        new = 0
        for img_tag in re.findall(r"<img[^>]*data-item-id[^>]*>", page_html):
            id_m = re.search(r'data-item-id="(\d+)"', img_tag)
            src_m = re.search(r'src="([^"]+)"', img_tag)
            if not id_m or not src_m or id_m.group(1) in seen_ids:
                continue
            original = _unwrap_resize_url(src_m.group(1))
            if original is None:
                continue
            seen_ids.add(id_m.group(1))
            if original not in urls:
                urls.append(original)
            new += 1
        return new

    with SB(
        uc=True,
        headless=True,
        headless2=True,
        user_data_dir=_PROFILE_DIR,
        locale_code="en",
        ad_block=True,  # ad-heavy pages can crash the headless browser mid-run
    ) as sb:
        sb.uc_open_with_reconnect(link, 4)
        sb.sleep(4)
        collect(sb.get_page_source())

        next_sel = 'button[aria-label*="next"]'
        empty_rounds = 0
        for _ in range(60):  # hard cap; carousels have a handful of slides
            try:
                if not sb.is_element_present(next_sel):
                    break
                disabled = sb.get_attribute(next_sel, "disabled")
                if disabled is not None:
                    break
                sb.click(next_sel)
            except Exception:
                break
            # Slides lazy-load — poll briefly for the new slide's img, and
            # only stop after two consecutive clicks that add nothing.
            added = 0
            for _ in range(5):
                sb.sleep(0.6)
                added = collect(sb.get_page_source())
                if added:
                    break
            empty_rounds = 0 if added else empty_rounds + 1
            if empty_rounds >= 2:
                break

    return urls


def scrape_images(link: str) -> list[str]:
    """Return the main gallery image URLs for a Thingiverse thing.

    The full gallery requires the browser scrape (no public API returns it
    anymore); the v2 API's default_image is the fallback when the browser
    run fails."""
    with _PROFILE_LOCK:
        with BROWSER_SESSION_LOCK:
            for attempt in range(2):
                reap_stale_profile_chromes(_PROFILE_DIR)
                try:
                    urls = _scrape_images_browser(link)
                    if urls:
                        return urls
                    break  # empty gallery — retrying won't add images
                except Exception as e:
                    if attempt == 0 and is_browser_death(e):
                        print(f"[thingiverse] browser died mid-run, retrying once: {e}")
                        time.sleep(3)
                        continue
                    print(f"[thingiverse] browser gallery scrape failed, falling back to API: {e}")
                    break
    return _scrape_images_api(link)


def probe_images() -> tuple[bool, str]:
    """Probe the image scraper against a known public thing."""
    try:
        urls = scrape_images(f"{THINGIVERSE_BASE}/thing:3539464")
        if urls:
            return True, f"{len(urls)} image(s) found"
        return False, "API returned no images"
    except Exception as e:
        return False, str(e)


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
