"""MakerWorld downloader.

Same architecture as the Cults3D downloader: SeleniumBase UC Mode
(undetected-chromedriver) with a persistent local Chrome profile at
backend/downloaders/makerworld_profile/ holding the MakerWorld login session
and Cloudflare clearance between runs. Gitignored; delete it to force a fresh
login.

Efficiency notes (tailored to MakerWorld, unlike Cults3D):
- The design metadata API is public and NOT behind Cloudflare — plain
  requests, no browser needed.
- The f3mf download API is behind Cloudflare AND requires a logged-in session,
  and a Python TLS fingerprint is challenged even with a valid cf_clearance
  (this is why the old implementation needed curl_cffi + manually pasted
  cookies). So the UC browser is used only to clear Cloudflare and hold the
  session; the f3mf API call itself is made by navigating the browser to the
  API URL (perfect fingerprint, no JS), and the signed CDN URL it returns is
  fetched with plain requests (the bblmw.com CDN is not Cloudflare-protected).
- Login uses the bambulab.com SSO form reached via the model page "Log In"
  button (input[name=account] / input[name=password]). After one successful
  login the profile session persists and credentials are no longer needed.

Headless behavior: headless by default (MAKERWORLD_HEADLESS=true in .env).
If Cloudflare cannot be cleared headless, one headed retry is attempted.
Set MAKERWORLD_HEADLESS=false to always run headed.

Login: MAKERWORLD_EMAIL / MAKERWORLD_PASSWORD from .env (saved via
Settings > 3D File Sites) are used when the profile session has expired.
"""

import json
import os
import re
import threading
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

# Load .env so MAKERWORLD_EMAIL / MAKERWORLD_PASSWORD are available when the
# downloader is used outside the Flask app (CLI, tests).
load_dotenv()

MAKERWORLD_BASE = "https://makerworld.com"
MAKERWORLD_API = "https://makerworld.com/api"

# Persistent Chrome profile — carries the MakerWorld session + Cloudflare
# clearance between runs. Gitignored; delete it to force a fresh login.
_PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "makerworld_profile")

# A single Chrome profile cannot be shared between concurrent browser
# instances, so serialize downloads process-wide.
_PROFILE_LOCK = threading.Lock()

_HEADLESS = os.environ.get("MAKERWORLD_HEADLESS", "true").strip().lower() not in ("0", "false", "no")

# The public design-service API is not behind Cloudflare — plain requests works.
_META_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": MAKERWORLD_BASE + "/",
}


class _CloudflareBlocked(RuntimeError):
    """Raised when the Cloudflare challenge could not be cleared."""


def extract_model_info(link: str) -> tuple[str, str | None]:
    """
    Return (design_id, instance_id_or_None) parsed from a MakerWorld URL.
    design_id is the numeric model ID (e.g. "2462393").
    instance_id is from the #profileId-NNNN hash fragment, if present.
    """
    match = re.search(r'makerworld\.com/[^/]+/models/(\d+)', link)
    if not match:
        raise ValueError(f"No MakerWorld model ID found in: {link}")
    design_id = match.group(1)
    instance_match = re.search(r'profileId[-:](\d+)', link)
    instance_id = instance_match.group(1) if instance_match else None
    return design_id, instance_id


def _require_seleniumbase():
    try:
        from seleniumbase import SB
        return SB
    except ImportError as exc:
        raise RuntimeError(
            "seleniumbase is not installed. Run: pip install seleniumbase"
        ) from exc


def _fetch_model_meta(design_id: str, instance_id: str | None) -> dict:
    """
    Call the design-service API (no auth, no Cloudflare) and return:
      {"design_id", "title", "instance_id", "dev_model_name"}
    """
    resp = requests.get(
        f"{MAKERWORLD_API}/v1/design-service/design/{design_id}",
        headers=_META_HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    design = resp.json()

    title = design.get("title") or f"makerworld_{design_id}"
    instances = design.get("instances") or []
    if not instances:
        raise RuntimeError(f"No instances found for MakerWorld design {design_id}")

    default_id = str(design.get("defaultInstanceId") or "")

    def find_instance(target_id: str) -> dict | None:
        for inst in instances:
            if str(inst.get("id")) == target_id:
                return inst
        return None

    if instance_id:
        inst = find_instance(instance_id) or instances[0]
    elif default_id:
        inst = find_instance(default_id) or instances[0]
    else:
        inst = instances[0]

    actual_id = str(inst["id"])
    compat = (inst.get("extention") or {}).get("modelInfo", {}).get("compatibility", {})
    dev_model_name = compat.get("devModelName") or ""

    return {
        "design_id": design_id,
        "title": title,
        "instance_id": actual_id,
        "dev_model_name": dev_model_name,
    }


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


def _is_logged_in(sb) -> bool:
    """The header shows a 'Log In' button when logged out."""
    try:
        return not sb.is_element_visible('button:contains("Log In")')
    except Exception:
        return True


def _dismiss_cookie_banner(sb) -> None:
    """Dismiss the 'We use cookies' banner — it overlays page controls."""
    for sel in ['button:contains("OK")', 'button:contains("Accept")']:
        try:
            if sb.is_element_visible(sel):
                sb.click(sel)
                sb.sleep(0.5)
                return
        except Exception:
            pass


def _verification_prompt_visible(sb) -> bool:
    """Bambu Lab email 2FA: a modal asking for a code sent to the user's email."""
    try:
        return sb.is_element_visible('input[placeholder*="Verification code"]')
    except Exception:
        return False


def _do_login(sb, email: str, password: str, headless: bool) -> None:
    """Log in via the 'Log In' button. MakerWorld uses bambulab.com SSO:
    clicking Log In on a model page redirects to bambulab.com/en-us/sign-in,
    which posts back to makerworld.com/api/sign-in/ticket on success. On some
    pages the same form appears as a modal instead of a redirect; both use
    input[name=account] / input[name=password].

    Bambu Lab may require an email verification code on a new browser profile.
    Headed runs wait for the human to type the code into the browser window;
    headless runs fail with guidance, since the code cannot be entered. The
    completed session persists in the profile, so this is a one-time step."""
    sb.click('button:contains("Log In")')

    # Wait for either the SSO redirect or the login modal.
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            if "bambulab.com" in sb.get_current_url() or sb.is_element_visible('input[name="account"]'):
                break
        except Exception:
            pass
        sb.sleep(0.5)

    _dismiss_cookie_banner(sb)
    sb.wait_for_element('input[name="account"]', timeout=15)
    sb.type('input[name="account"]', email)
    sb.type('input[name="password"]', password)

    for btn_sel in ['button[type="submit"]', 'button:contains("Log In")', 'button:contains("Continue")']:
        try:
            if sb.is_element_visible(btn_sel):
                sb.click(btn_sel)
                break
        except Exception:
            continue

    # Wait until we are back on makerworld.com and logged in. A verification
    # code prompt extends the wait so a human can complete it (headed only).
    verification_seen = False
    deadline = time.time() + 150
    while time.time() < deadline:
        try:
            url = sb.get_current_url()
            if "makerworld.com" in url and "bambulab.com" not in url and _is_logged_in(sb):
                return
            if _verification_prompt_visible(sb):
                if headless:
                    raise RuntimeError(
                        "MakerWorld requires an email verification code for this login. "
                        "Run once headed (set MAKERWORLD_HEADLESS=false in .env) and type "
                        "the code into the browser window; the session then persists."
                    )
                if not verification_seen:
                    verification_seen = True
                    print("⚠️ MakerWorld sent a verification code to your email. "
                          "Type it into the browser window to finish logging in.")
        except RuntimeError:
            raise
        except Exception:
            pass
        sb.sleep(1)

    if not _is_logged_in(sb):
        raise RuntimeError("MakerWorld login failed. Check your credentials in Settings > 3D File Sites.")


def _ensure_logged_in(sb, email: str | None, password: str | None, headless: bool) -> None:
    if _is_logged_in(sb):
        return
    if not email or not password:
        raise RuntimeError(
            "MakerWorld login required to download models. "
            "Add your email and password in Settings > 3D File Sites."
        )
    _do_login(sb, email, password, headless)


def _get_download_url(sb, instance_id: str, dev_model_name: str) -> tuple[str, str]:
    """
    Resolve the signed CDN URL for an instance by navigating the browser to
    the f3mf API URL. Done in-browser because the API sits behind Cloudflare
    and challenges non-browser TLS fingerprints even with valid cookies.
    Returns (signed_cdn_url, filename).
    """
    params = f"type=download&fileType="
    if dev_model_name:
        params += f"&devModelName={quote(dev_model_name)}"
    api_url = f"{MAKERWORLD_API}/v1/design-service/instance/{instance_id}/f3mf?{params}"

    sb.open(api_url)
    sb.sleep(1)
    if not _wait_for_cloudflare(sb, 20):
        raise _CloudflareBlocked("Cloudflare challenge blocked the MakerWorld download API.")

    body = sb.get_text("body") or ""
    # Strip any pretty-print wrapper Chrome adds around JSON responses.
    body = body.replace("Pretty-print", "").strip()
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        raise RuntimeError(f"MakerWorld download API returned non-JSON: {body[:300]}")

    if result.get("error"):
        raise RuntimeError(f"MakerWorld download API error: {result['error']}")

    cdn_url = result.get("url")
    name = result.get("name") or f"model_{instance_id}.3mf"
    if not cdn_url:
        raise RuntimeError(f"MakerWorld API returned no download URL: {result}")
    return cdn_url, name


def _download_attempt(
    link: str,
    instance_id: str | None,
    email: str | None,
    password: str | None,
    headless: bool,
) -> tuple[str, bytes]:
    design_id, url_instance_id = extract_model_info(link)
    meta = _fetch_model_meta(design_id, instance_id or url_instance_id)
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
            # then allow time for a manual solve. Guarded so a missing pyautogui
            # never triggers SeleniumBase's mid-run auto-installer.
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

        _ensure_logged_in(sb, email, password, headless)
        cdn_url, raw_name = _get_download_url(sb, meta["instance_id"], meta["dev_model_name"])

    # CDN download — signed URL, no Cloudflare on bblmw.com
    resp = requests.get(
        cdn_url,
        headers={"User-Agent": _META_HEADERS["User-Agent"], "Referer": MAKERWORLD_BASE + "/"},
        timeout=120,
    )
    resp.raise_for_status()

    safe_name = re.sub(r'[^\w\-.]', '_', raw_name)
    if not safe_name.lower().endswith('.3mf'):
        safe_name += '.3mf'

    return safe_name, resp.content


def download_3mf(link_or_design_id: str, instance_id: str | None = None) -> tuple[str, bytes]:
    """
    Download the 3MF file for a MakerWorld model.
    Accepts a full model URL or a bare design ID. Returns (filename, file_bytes).
    Uses the persistent UC profile; logs in with MAKERWORLD_EMAIL /
    MAKERWORLD_PASSWORD from .env when the session has expired.
    """
    link = (
        link_or_design_id
        if "makerworld.com" in link_or_design_id
        else f"{MAKERWORLD_BASE}/en/models/{link_or_design_id}"
    )
    email = os.environ.get("MAKERWORLD_EMAIL", "").strip() or None
    password = os.environ.get("MAKERWORLD_PASSWORD", "").strip() or None

    with _PROFILE_LOCK:
        if not _HEADLESS:
            return _download_attempt(link, instance_id, email, password, headless=False)

        # Headless first; fall back to one headed attempt if Cloudflare blocks it.
        try:
            return _download_attempt(link, instance_id, email, password, headless=True)
        except _CloudflareBlocked:
            return _download_attempt(link, instance_id, email, password, headless=False)


def probe() -> tuple[bool, str]:
    """
    Probe the public metadata API and check login readiness. Does not launch a
    browser — a valid profile session can only be confirmed by a real download.
    """
    try:
        _fetch_model_meta("2462393", None)
    except Exception as e:
        return False, f"Metadata API error: {e}"

    if os.path.isdir(_PROFILE_DIR):
        return True, "Metadata API OK, session profile present"

    if os.environ.get("MAKERWORLD_EMAIL", "").strip() and os.environ.get("MAKERWORLD_PASSWORD", "").strip():
        return True, "Metadata API OK, credentials configured"

    return False, "No MakerWorld login — add email and password in Settings > 3D File Sites"
