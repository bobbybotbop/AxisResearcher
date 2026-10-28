import io
import json
import os
import re
import tempfile
import time
import zipfile

import requests

CULTS3D_BASE = "https://cults3d.com"
_COOKIE_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".cults3d_cookies.json")
)


class PaidModelError(ValueError):
    """Raised when the requested model requires payment."""


def extract_slug(link: str) -> str:
    match = re.search(r"cults3d\.com/[^/]+/3d-model/[^/]+/([^/?#]+)", link)
    if not match:
        raise ValueError(f"No Cults3D model slug found in: {link}")
    return match.group(1)


def load_cookies_from_browser() -> str:
    """
    Attempt to read Cults3D cookies from an installed browser.
    Chrome 127+ uses App-Bound Encryption that blocks this without admin
    privileges. Firefox works reliably if the user is logged in there.
    """
    try:
        import browser_cookie3
    except ImportError:
        raise RuntimeError("browser_cookie3 is not installed.")

    errors: list[str] = []

    for browser_name, loader in [
        ("Firefox", lambda: browser_cookie3.firefox(domain_name="cults3d.com")),
        ("Edge", lambda: browser_cookie3.edge(domain_name="cults3d.com")),
        ("Chrome", lambda: browser_cookie3.chrome(domain_name="cults3d.com")),
    ]:
        try:
            cjar = loader()
            parts = [f"{c.name}={c.value}" for c in cjar if c.value]
            if parts:
                return "; ".join(parts)
        except Exception as e:
            err_str = str(e)
            if "admin" in err_str.lower() or "RequiresAdmin" in type(e).__name__:
                errors.append(
                    f"{browser_name}: Chrome 127+ cookies require admin access to read automatically."
                )
            else:
                errors.append(f"{browser_name}: {err_str}")

    raise RuntimeError(
        "Could not auto-load cookies from any browser. "
        + " | ".join(errors)
        + " — Use email/password login in Settings instead, or paste cookies manually from DevTools."
    )


def _require_sb_cdp():
    try:
        from seleniumbase import sb_cdp
        return sb_cdp
    except ImportError as exc:
        raise RuntimeError(
            "seleniumbase is not installed. Run: pip install seleniumbase"
        ) from exc


def _csrf_from_html(html: str) -> str:
    match = re.search(r'name="authenticity_token"\s+value="([^"]+)"', html)
    if not match:
        match = re.search(r'value="([^"]+)"\s+name="authenticity_token"', html)
    if not match:
        raise RuntimeError("Could not find CSRF token in page HTML")
    return match.group(1)


def _dismiss_popups(sb) -> None:
    try:
        if sb.is_element_visible('button:contains("CONFIRM")'):
            sb.click('button:contains("CONFIRM")')
            time.sleep(0.5)
    except Exception:
        pass


def _inject_cookie_string(sb, cookie_string: str) -> None:
    """Convert a browser cookie string to SeleniumBase JSON format and load it."""
    cookies = []
    for part in cookie_string.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            name = name.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value.strip(),
                    "domain": ".cults3d.com",
                    "path": "/",
                })
    if not cookies:
        return
    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", delete=False, mode="w", encoding="utf-8"
    )
    json.dump(cookies, tmp)
    tmp.close()
    try:
        sb.load_cookies(tmp.name)
    except Exception:
        pass
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _do_login(sb, email: str, password: str) -> None:
    sb.goto(f"{CULTS3D_BASE}/en/users/sign-in")
    time.sleep(2)
    _dismiss_popups(sb)
    sb.type('input[name="user[email]"]', email)
    sb.type('input[name="user[password]"]', password)
    time.sleep(0.3)
    sb.evaluate('document.querySelector(\'form[action*="sign-in"]\').submit()')
    time.sleep(4)
    if "sign-in" in sb.get_current_url().lower():
        raise RuntimeError("Cults3D login failed. Check email/password.")
    try:
        sb.save_cookies(_COOKIE_FILE)
    except Exception:
        pass


def _check_price(html: str) -> None:
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
                f"Paid model ({price} {currency}). Only free models can be downloaded."
            )
        return

    prices = re.findall(r'class="tbox-title crea-price"[^>]*>\s*([^<]+)', html)
    if prices:
        first = prices[0].strip()
        if first.lower() != "free" and re.search(r"[\d.]", first):
            raise PaidModelError(
                f"Paid model ({first}). Only free models can be downloaded."
            )


def _extract_file_links(html: str) -> list[dict]:
    files: list[dict] = []
    seen: set[str] = set()

    def add(name: str, url: str) -> None:
        if url not in seen:
            seen.add(url)
            files.append({"name": name, "url": url})

    for url in re.findall(
        r'href="(https://fbi\.cults3d\.com/uploaders/\d+/creation-file/[^"]+)"',
        html,
        re.IGNORECASE,
    ):
        add(url.split("/")[-1].split("?")[0], url)

    for path in re.findall(
        r'href="(/en/(?:orders/[^/]+/)?creation.?file[^"]*)"',
        html,
        re.IGNORECASE,
    ):
        url = CULTS3D_BASE + path
        add(path.split("/")[-1].split("?")[0] or f"file_{len(files)}", url)

    return files


def _place_free_order(sb, link: str, slug: str) -> list[dict]:
    sb.goto(link)
    time.sleep(3)
    _dismiss_popups(sb)

    html = sb.get_page_source()
    files = _extract_file_links(html)
    if files:
        return files

    # Click the download/order button
    clicked = False
    for selector in [
        'a[href*="free_orders"]',
        'a:contains("Download")',
        'button:contains("Download")',
        ".crea-dl a",
        "a.btn-dl",
    ]:
        try:
            if sb.is_element_visible(selector):
                sb.click(selector)
                time.sleep(3)
                _dismiss_popups(sb)
                clicked = True
                break
        except Exception:
            continue

    if clicked:
        for confirm_selector in [
            'button:contains("Confirm")',
            'input[type="submit"][value*="Order"]',
            'button:contains("Order")',
            '.modal button[type="submit"]',
        ]:
            try:
                if sb.is_element_visible(confirm_selector):
                    sb.click(confirm_selector)
                    time.sleep(3)
                    break
            except Exception:
                continue

        html = sb.get_page_source()
        files = _extract_file_links(html)
        if files:
            return files

    # Fallback: AJAX order placement using the browser's authenticated cookies.
    # The browser has already passed Cloudflare, so its cookies can be reused
    # in a plain requests call for this XHR-style endpoint.
    html = sb.get_page_source()
    cookie_str = sb.get_cookie_string()
    csrf = None
    try:
        csrf = _csrf_from_html(html)
    except RuntimeError:
        pass

    if csrf and cookie_str:
        order_url = f"{CULTS3D_BASE}/en/free_orders?creation_slug={slug}"
        try:
            r = requests.post(
                order_url,
                data={"authenticity_token": csrf},
                headers={
                    "Cookie": cookie_str,
                    "Referer": link,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/131.0.0.0 Safari/537.36"
                    ),
                },
                timeout=30,
                allow_redirects=True,
            )
            r.raise_for_status()

            ct = r.headers.get("Content-Type", "")
            if "json" in ct:
                data = r.json()
                if "error" not in data:
                    if "files" in data:
                        return [
                            {"name": f.get("name", f"file_{i}"), "url": f["url"]}
                            for i, f in enumerate(data["files"])
                            if "url" in f
                        ]
                    for key in ("download_url", "redirect_url", "location", "url"):
                        if key in data:
                            target = data[key]
                            if not target.startswith("http"):
                                target = CULTS3D_BASE + target
                            sb.goto(target)
                            time.sleep(2)
                            files = _extract_file_links(sb.get_page_source())
                            if files:
                                return files
                            break

            files = _extract_file_links(r.text)
            if files:
                return files
        except Exception:
            pass

    sb.goto(link)
    time.sleep(3)
    files = _extract_file_links(sb.get_page_source())
    if files:
        return files

    raise RuntimeError(
        "Could not extract file download URLs after placing the free order. "
        "The site's response format may have changed."
    )


def probe() -> tuple[bool, str]:
    try:
        r = requests.get(
            CULTS3D_BASE,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
            },
            timeout=10,
        )
        # Cloudflare may return 403 for plain requests, but the site is still
        # reachable - SeleniumBase will bypass it during actual downloads.
        if r.status_code in (200, 403):
            return True, "Cults3D reachable"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def stream_zip(
    link: str,
    cookies: str | None = None,
    email: str | None = None,
    password: str | None = None,
    file_download_delay: float = 0.0,
) -> tuple[str, bytes]:
    slug = extract_slug(link)

    resolved_cookies = cookies or os.environ.get("CULTS3D_COOKIES", "").strip() or None
    resolved_email = email or os.environ.get("CULTS3D_EMAIL", "").strip() or None
    resolved_password = password or os.environ.get("CULTS3D_PASSWORD", "").strip() or None

    sb_cdp = _require_sb_cdp()
    sb = None
    try:
        sb = sb_cdp.Chrome()

        # Navigate to domain first so Cloudflare challenge is resolved and
        # cookies can be loaded into the correct origin context.
        sb.goto(CULTS3D_BASE)
        time.sleep(2)
        _dismiss_popups(sb)

        if os.path.exists(_COOKIE_FILE):
            try:
                sb.load_cookies(_COOKIE_FILE)
            except Exception:
                pass

        sb.goto(link)
        time.sleep(3)
        _dismiss_popups(sb)

        if re.search(r"/(sign.?in|log.?in)", sb.get_current_url(), re.IGNORECASE):
            if resolved_cookies:
                _inject_cookie_string(sb, resolved_cookies)
                sb.goto(link)
                time.sleep(3)
                _dismiss_popups(sb)

            if re.search(r"/(sign.?in|log.?in)", sb.get_current_url(), re.IGNORECASE):
                if not resolved_email or not resolved_password:
                    raise RuntimeError(
                        "Cults3D credentials required. "
                        "Add your email and password in Settings > 3D File Sites."
                    )
                _do_login(sb, resolved_email, resolved_password)
                sb.goto(link)
                time.sleep(3)
                _dismiss_popups(sb)

            if re.search(r"/(sign.?in|log.?in)", sb.get_current_url(), re.IGNORECASE):
                raise RuntimeError(
                    "Cults3D authentication failed. "
                    "If using cookies, they may be expired; update them in Settings. "
                    "If using email/password, check your credentials in Settings."
                )

        _check_price(sb.get_page_source())

        files = _place_free_order(sb, link, slug)

        if not files:
            raise RuntimeError("No downloadable files found for this Cults3D model.")

        cookie_str = sb.get_cookie_string()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, f in enumerate(files):
                if i > 0 and file_download_delay > 0:
                    time.sleep(file_download_delay)
                r = requests.get(
                    f["url"],
                    headers={
                        "Cookie": cookie_str,
                        "Referer": link,
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"
                        ),
                    },
                    timeout=60,
                )
                r.raise_for_status()
                zf.writestr(f["name"], r.content)

        return f"{slug}.zip", buf.getvalue()

    finally:
        if sb is not None:
            try:
                sb.quit()
            except Exception:
                pass
