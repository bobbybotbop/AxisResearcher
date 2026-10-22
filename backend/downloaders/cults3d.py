import io
import json
import os
import re
import zipfile
import cloudscraper

CULTS3D_BASE = "https://cults3d.com"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


class PaidModelError(ValueError):
    """Raised when the requested model requires payment."""


def extract_slug(link: str) -> str:
    """Return the creation slug from a Cults3D URL."""
    match = re.search(r"cults3d\.com/[^/]+/3d-model/[^/]+/([^/?#]+)", link)
    if not match:
        raise ValueError(f"No Cults3D model slug found in: {link}")
    return match.group(1)


def _make_session() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )


def _csrf_from_html(html: str) -> str:
    match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', html)
    if not match:
        # Try alternate attribute order
        match = re.search(r'value="([^"]+)"\s+name="authenticity_token"', html)
    if not match:
        raise RuntimeError("Could not find CSRF token in page HTML")
    return match.group(1)


def _check_price(html: str, link: str) -> None:
    """
    Parse JSON-LD embedded in the page HTML.
    Raises PaidModelError if offers[0].price > 0.
    """
    for raw in re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        offers = data.get("offers") or []
        if not offers:
            continue
        price = float(offers[0].get("price", 0))
        currency = offers[0].get("priceCurrency", "")
        if price > 0:
            raise PaidModelError(
                f"Paid model ({price} {currency}) — only free models can be downloaded."
            )
        return  # price == 0 → free, stop checking

    # Fallback: look for a price element in the HTML
    prices = re.findall(r'class="tbox-title crea-price"[^>]*>\s*([^<]+)', html)
    if prices:
        first = prices[0].strip()
        if first.lower() != "free" and re.search(r'[\d.]', first):
            raise PaidModelError(
                f"Paid model ({first}) — only free models can be downloaded."
            )


def _login(session: cloudscraper.CloudScraper, email: str, password: str) -> None:
    login_url = f"{CULTS3D_BASE}/en/users/sign-in"

    r = session.get(login_url, headers=_BROWSER_HEADERS, timeout=20)
    r.raise_for_status()
    csrf = _csrf_from_html(r.text)

    login_r = session.post(
        login_url,
        data={
            "authenticity_token": csrf,
            "user[email]": email,
            "user[password]": password,
            "commit": "",
        },
        headers={
            **_BROWSER_HEADERS,
            "Referer": login_url,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        allow_redirects=True,
        timeout=20,
    )
    login_r.raise_for_status()

    # If still on a login/sign-in page the credentials were wrong
    if re.search(r"/(sign.?in|log.?in)", login_r.url, re.IGNORECASE):
        raise RuntimeError("Cults3D login failed — check CULTS3D_EMAIL / CULTS3D_PASSWORD.")

    if re.search(r"(invalid|incorrect|wrong).{0,30}(email|password|credential)", login_r.text, re.IGNORECASE):
        raise RuntimeError("Cults3D login failed — invalid email or password.")


def _extract_file_links(html: str) -> list[dict]:
    """
    Look for direct file download URLs in a page's HTML.
    Returns [{"name": ..., "url": ...}, ...].
    """
    files: list[dict] = []
    seen: set[str] = set()

    def add(name: str, url: str) -> None:
        if url not in seen:
            seen.add(url)
            files.append({"name": name, "url": url})

    # CDN direct links (appear on the order/download page once the order is placed)
    for url in re.findall(
        r'href="(https://fbi\.cults3d\.com/uploaders/\d+/creation-file/[^"]+)"',
        html,
        re.IGNORECASE,
    ):
        add(url.split("/")[-1].split("?")[0], url)

    # Relative order / creation-file download paths
    for path in re.findall(
        r'href="(/en/(?:orders/[^/]+/)?creation.?file[^"]*)"',
        html,
        re.IGNORECASE,
    ):
        url = CULTS3D_BASE + path
        add(path.split("/")[-1].split("?")[0] or f"file_{len(files)}", url)

    return files


def _place_free_order_and_get_files(
    session: cloudscraper.CloudScraper, link: str, slug: str
) -> list[dict]:
    """
    POST to /en/free_orders, follow the response, and return a list of
    {"name", "url"} dicts for each file.
    """
    # GET model page for CSRF token; also check if files are already visible
    page_r = session.get(link, headers=_BROWSER_HEADERS, timeout=20)
    page_r.raise_for_status()
    csrf = _csrf_from_html(page_r.text)

    # If download links are already embedded (model previously ordered), use them
    already = _extract_file_links(page_r.text)
    if already:
        return already

    order_url = f"{CULTS3D_BASE}/en/free_orders?creation_slug={slug}"

    # Try JSON first — gives us a structured response without a full page redirect
    json_r = session.post(
        order_url,
        data={"authenticity_token": csrf},
        headers={
            **_BROWSER_HEADERS,
            "Referer": link,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        },
        allow_redirects=True,
        timeout=30,
    )
    json_r.raise_for_status()

    ct = json_r.headers.get("Content-Type", "")
    if "json" in ct:
        data = json_r.json()
        if "error" in data:
            raise RuntimeError(f"Cults3D order error: {data['error']}")

        # Possible shapes: {files: [{url, name}]}, {download_url}, {redirect_url}
        if "files" in data:
            return [{"name": f.get("name", f"file_{i}"), "url": f["url"]}
                    for i, f in enumerate(data["files"]) if "url" in f]

        for key in ("download_url", "redirect_url", "location", "url"):
            if key in data:
                target = data[key]
                if not target.startswith("http"):
                    target = CULTS3D_BASE + target
                follow_r = session.get(target, headers=_BROWSER_HEADERS, timeout=20)
                follow_r.raise_for_status()
                files = _extract_file_links(follow_r.text)
                if files:
                    return files

    # HTML redirect path — look for files in the response body
    files = _extract_file_links(json_r.text)
    if files:
        return files

    # Last resort: reload the model page (now that the free order exists the page
    # should expose download links for logged-in users)
    reload_r = session.get(link, headers=_BROWSER_HEADERS, timeout=20)
    reload_r.raise_for_status()
    files = _extract_file_links(reload_r.text)
    if files:
        return files

    raise RuntimeError(
        "Could not extract file download URLs after placing the free order. "
        "The site's response format may have changed."
    )


def probe() -> tuple[bool, str]:
    try:
        session = _make_session()
        r = session.get(CULTS3D_BASE, headers=_BROWSER_HEADERS, timeout=10)
        r.raise_for_status()
        return True, "Cults3D reachable"
    except Exception as e:
        return False, str(e)


def stream_zip(
    link: str,
    email: str | None = None,
    password: str | None = None,
    file_download_delay: float = 0.0,
) -> tuple[str, bytes]:
    """
    Download all files for a free Cults3D creation and return (zip_filename, zip_bytes).

    Raises PaidModelError (a ValueError) if the model costs money.
    Requires CULTS3D_EMAIL and CULTS3D_PASSWORD env vars (or explicit args).
    """
    email = email or os.environ.get("CULTS3D_EMAIL", "")
    password = password or os.environ.get("CULTS3D_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Cults3D credentials required — set CULTS3D_EMAIL and CULTS3D_PASSWORD "
            "in the .env file."
        )

    slug = extract_slug(link)
    session = _make_session()

    # Warm up the session / pass Cloudflare challenge
    session.get(CULTS3D_BASE, headers=_BROWSER_HEADERS, timeout=15)

    # Fetch model page and check price (no auth needed for price check)
    page_r = session.get(link, headers=_BROWSER_HEADERS, timeout=20)
    page_r.raise_for_status()
    _check_price(page_r.text, link)

    # Authenticate
    _login(session, email, password)

    # Place free order and collect file URLs
    import time
    files = _place_free_order_and_get_files(session, link, slug)

    if not files:
        raise RuntimeError("No downloadable files found for this Cults3D model.")

    # Download each file and pack into a zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, f in enumerate(files):
            if i > 0 and file_download_delay > 0:
                time.sleep(file_download_delay)
            dr = session.get(
                f["url"],
                headers={**_BROWSER_HEADERS, "Referer": link},
                timeout=60,
            )
            dr.raise_for_status()
            zf.writestr(f["name"], dr.content)

    return f"{slug}.zip", buf.getvalue()
