"""Cults3D downloader.

Uses SeleniumBase UC Mode (undetected-chromedriver) with a persistent local
Chrome profile instead of connecting to an external browser. The profile at
backend/downloaders/cults3d_profile/ keeps the Cults3D login session and
Cloudflare clearance across runs, so no external browser (e.g. BrowserOS neo)
is required.

Headless behavior:
- Runs headless by default (CULTS3D_HEADLESS=true in .env).
- If a Cloudflare challenge cannot be cleared headless, the download is
  retried once in a headed window, where the challenge can be solved
  automatically (uc_gui_handle_captcha) or manually by the user.
- Set CULTS3D_HEADLESS=false to always run headed.

Login: CULTS3D_EMAIL / CULTS3D_PASSWORD from .env are used when the profile
is not already logged in. After one successful login the profile session
persists and credentials are no longer needed.
"""

import io
import json
import os
import re
import threading
import time
import zipfile

import requests

CULTS3D_BASE = "https://cults3d.com"

# Persistent Chrome profile — carries the Cults3D session + Cloudflare
# clearance between runs. Gitignored; delete it to force a fresh login.
_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cults3d_profile")

# A single Chrome profile cannot be shared between concurrent browser
# instances, so serialize downloads process-wide.
_PROFILE_LOCK = threading.Lock()

_HEADLESS = os.environ.get("CULTS3D_HEADLESS", "true").strip().lower() not in ("0", "false", "no")

# Used only for the plain-requests probe() and as a fallback download UA.
# The browser itself must NOT be given a pinned UA: a UA that disagrees with
# the installed Chrome version (sec-ch-ua client hints) is a bot signal to
# Cloudflare. Downloads instead reuse the browser's real UA (see stream_zip).
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class PaidModelError(ValueError):
    """Raised when the requested model requires payment."""


class _CloudflareBlocked(RuntimeError):
    """Raised when the Cloudflare challenge could not be cleared."""


def extract_slug(link: str) -> str:
    match = re.search(r"cults3d\.com/[^/]+/3d-model/[^/]+/([^/?#]+)", link)
    if not match:
        raise ValueError(f"No Cults3D model slug found in: {link}")
    return match.group(1)


def _require_seleniumbase():
    try:
        from seleniumbase import SB
        return SB
    except ImportError as exc:
        raise RuntimeError(
            "seleniumbase is not installed. Run: pip install seleniumbase"
        ) from exc


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

    # Order page "DOWNLOAD ALL" link, e.g. /en/downloads/195749838?creation=<slug>
    for path, creation in re.findall(
        r'href="(/en/downloads/\d+\?creation=([^"&]+))"',
        html,
        re.IGNORECASE,
    ):
        add(f"{creation}.zip", CULTS3D_BASE + path)

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


def _wait_for_cloudflare(sb, timeout: float = 20) -> bool:
    """Poll until the Cloudflare challenge page is gone. Returns False if it persists."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            title = sb.get_title() or ""
        except Exception:
            title = ""
        try:
            body = sb.get_text("body") or ""
        except Exception:
            body = ""
        if "Just a moment" not in title and "Performing security verification" not in body:
            return True
        sb.sleep(1)
    return False


def _is_on_sign_in(url: str) -> bool:
    return bool(re.search(r"/(sign.?in|log.?in)", url, re.IGNORECASE))


def _dismiss_overlays(sb) -> None:
    """Dismiss cookie-consent banners/modals that overlay page controls.

    The consent flow is two steps: a banner with CONFIRM, then a follow-up
    dialog ("We have received your choices…") with an OK button. Both block
    clicks on the underlying page until dismissed.
    """
    try:
        if sb.is_element_visible('button:contains("CONFIRM")'):
            sb.click('button:contains("CONFIRM")')
            sb.sleep(1)
    except Exception:
        pass
    try:
        ok_xpath = '//button[normalize-space(text())="OK"]'
        if sb.is_element_visible(ok_xpath, by="xpath"):
            sb.click(ok_xpath, by="xpath")
            sb.sleep(1)
    except Exception:
        pass


def _do_login(sb, email: str, password: str) -> None:
    sb.uc_open_with_reconnect(f"{CULTS3D_BASE}/en/users/sign-in", 4)
    if not _wait_for_cloudflare(sb, 20):
        raise _CloudflareBlocked("Cloudflare challenge blocked the Cults3D sign-in page.")
    sb.wait_for_element("form", timeout=15)

    # A cookie-consent modal can overlay the form on a fresh profile and make
    # the inputs non-interactable — dismiss it first.
    _dismiss_overlays(sb)

    # The sign-in form (id "new-session") uses #session_email /
    # #registration_password. Fall back to the Rails field names.
    email_sel = "#session_email"
    if not sb.is_element_present(email_sel):
        email_sel = 'input[name="user[email]"]'
    password_sel = "#registration_password"
    if not sb.is_element_present(password_sel):
        password_sel = 'input[name="user[password]"]'

    try:
        sb.type(email_sel, email)
        sb.type(password_sel, password)
    except Exception:
        # If the inputs stay non-interactable (overlay, animation), set the
        # values via JS — the real submit click below still fires the handlers.
        sb.js_update_text(email_sel, email)
        sb.js_update_text(password_sel, password)

    # A real button click, not JS form.submit() — Cults3D binds handlers to it.
    # (uc_click's disconnect/reconnect closes the tab in headless mode, so a
    # plain click is used here and for DOWNLOAD below.)
    for btn_sel in ['input[type="submit"][value="Log in"]', 'button:contains("Log in")', 'input[type="submit"]', 'button[type="submit"]']:
        if sb.is_element_visible(btn_sel):
            sb.click(btn_sel)
            break

    # Don't wait for networkidle — ads/analytics keep connections alive forever.
    # Instead poll until the URL leaves the sign-in page.
    deadline = time.time() + 20
    while time.time() < deadline and _is_on_sign_in(sb.get_current_url()):
        sb.sleep(1)
    if _is_on_sign_in(sb.get_current_url()):
        raise RuntimeError("Cults3D login failed. Check your credentials in Settings.")


def _ensure_logged_in(sb, email: str | None, password: str | None, link: str) -> None:
    """If the current page indicates a logged-out state, log in and navigate back."""
    needs_login = _is_on_sign_in(sb.get_current_url())

    if not needs_login:
        # Also check the navbar text — the SIGN IN element is not always an
        # <a> inside <nav>, so a scoped text check is more reliable.
        try:
            needs_login = sb.is_text_visible("SIGN IN", "nav")
        except Exception:
            pass

    if not needs_login:
        return

    if not email or not password:
        raise RuntimeError(
            "Cults3D credentials required. "
            "Add your email and password in Settings > 3D File Sites."
        )
    _do_login(sb, email, password)
    sb.uc_open_with_reconnect(link, 3)
    if not _wait_for_cloudflare(sb, 20):
        raise _CloudflareBlocked("Cloudflare challenge blocked the Cults3D model page after login.")
    _dismiss_overlays(sb)


def _place_free_order(sb, link: str) -> list[dict]:
    """Click the free download button and return extracted file links."""
    _dismiss_overlays(sb)
    files = _extract_file_links(sb.get_page_source())
    if files:
        return files

    # The model page has a single "DOWNLOAD FREE" button for free models.
    # Note: :contains is case-sensitive and the all-caps "DOWNLOAD" variant
    # matches nothing here — "Download" is the working selector. Scope the
    # search to <button> elements: a page-wide text search would first match
    # FAQ anchors like "How can I download files?" and navigate away.
    try:
        if sb.is_element_visible('button:contains("Download")'):
            sb.click('button:contains("Download")')
            # Lands on the order page (/en/orders/<id>) with the real file links
            deadline = time.time() + 15
            while time.time() < deadline and "/orders/" not in sb.get_current_url():
                sb.sleep(0.5)
            sb.sleep(2)
            # Some models show a license confirmation modal first
            for confirm_sel in [
                'button:contains("Confirm")',
                'button:contains("Order")',
                '.modal button[type="submit"]',
            ]:
                try:
                    if sb.is_element_visible(confirm_sel):
                        sb.click(confirm_sel)
                        sb.sleep(3)
                        break
                except Exception:
                    continue
    except Exception:
        pass

    return _extract_file_links(sb.get_page_source())


def load_cookies_from_browser() -> str:
    """No longer used — the local persistent profile maintains the Cults3D session."""
    raise RuntimeError(
        "Auto-loading cookies from an installed browser is no longer needed. "
        "The downloader keeps its own persistent profile, so once you are logged in "
        "(via Settings > 3D File Sites) the session persists automatically."
    )


def probe() -> tuple[bool, str]:
    try:
        r = requests.get(
            CULTS3D_BASE,
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        # Cloudflare may return 403 for plain requests — the site is still reachable
        if r.status_code in (200, 403):
            return True, "Cults3D reachable"
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def _stream_zip_attempt(
    link: str,
    email: str | None,
    password: str | None,
    file_download_delay: float,
    headless: bool,
) -> tuple[str, bytes]:
    slug = extract_slug(link)
    SB = _require_seleniumbase()

    with SB(
        uc=True,
        headless=headless,
        headless2=headless,
        user_data_dir=_PROFILE_DIR,
        locale_code="en",
    ) as sb:
        sb.uc_open_with_reconnect(link, 4)
        if not _wait_for_cloudflare(sb, 20):
            if headless:
                raise _CloudflareBlocked(
                    "Cloudflare challenge could not be cleared in headless mode."
                )
            # Headed: try the automatic Turnstile click (requires pyautogui),
            # then allow time for a manual solve if the challenge needs human
            # interaction. Guarded so a missing pyautogui never triggers
            # SeleniumBase's mid-run auto-installer.
            import importlib.util
            if importlib.util.find_spec("pyautogui") is not None:
                try:
                    sb.driver.uc_gui_handle_captcha()
                except Exception:
                    pass
            if not _wait_for_cloudflare(sb, 60):
                raise _CloudflareBlocked(
                    "Cloudflare challenge could not be cleared. Try again."
                )

        _ensure_logged_in(sb, email, password, link)

        _check_price(sb.get_page_source())

        files = _place_free_order(sb, link)
        if not files:
            raise RuntimeError("No downloadable files found for this Cults3D model.")

        # Grab the browser's cookies (includes cf_clearance + session) and its
        # real UA — cf_clearance is bound to the user agent, so the follow-up
        # requests must present the same one.
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in sb.get_cookies())
        try:
            download_ua = sb.get_user_agent() or _USER_AGENT
        except Exception:
            download_ua = _USER_AGENT

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
                        "User-Agent": download_ua,
                    },
                    timeout=60,
                )
                r.raise_for_status()
                content = r.content
                # Cults3D's "DOWNLOAD ALL" endpoint returns a zip itself —
                # unwrap it so the output contains the actual 3D files,
                # not a nested zip (single_file mode needs this too).
                if content[:4] == b"PK\x03\x04":
                    try:
                        with zipfile.ZipFile(io.BytesIO(content)) as inner:
                            for info in inner.infolist():
                                if info.is_dir():
                                    continue
                                zf.writestr(info.filename, inner.read(info.filename))
                        continue
                    except zipfile.BadZipFile:
                        pass
                zf.writestr(f["name"], content)

        return f"{slug}.zip", buf.getvalue()


def stream_zip(
    link: str,
    cookies: str | None = None,
    email: str | None = None,
    password: str | None = None,
    file_download_delay: float = 0.0,
) -> tuple[str, bytes]:
    resolved_email = email or os.environ.get("CULTS3D_EMAIL", "").strip() or None
    resolved_password = password or os.environ.get("CULTS3D_PASSWORD", "").strip() or None

    with _PROFILE_LOCK:
        if not _HEADLESS:
            return _stream_zip_attempt(
                link, resolved_email, resolved_password, file_download_delay, headless=False
            )

        # Headless first; fall back to one headed attempt if Cloudflare blocks it.
        try:
            return _stream_zip_attempt(
                link, resolved_email, resolved_password, file_download_delay, headless=True
            )
        except _CloudflareBlocked:
            return _stream_zip_attempt(
                link, resolved_email, resolved_password, file_download_delay, headless=False
            )
