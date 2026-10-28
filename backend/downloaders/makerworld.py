import os
import re
import requests
from curl_cffi import requests as cffi_requests

MAKERWORLD_BASE = "https://makerworld.com"
MAKERWORLD_API = "https://makerworld.com/api"

# The public design-service API is not behind Cloudflare — plain requests works.
_META_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": MAKERWORLD_BASE + "/",
}

# The download endpoint is behind Cloudflare and requires Chrome TLS impersonation.
_CFFI_HEADERS = {
    "Accept": "application/json",
    "Referer": MAKERWORLD_BASE + "/",
    "Origin": MAKERWORLD_BASE,
}


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


def _get_cookies() -> str:
    """Return MAKERWORLD_COOKIES from env, or raise with a helpful message."""
    cookies = os.environ.get("MAKERWORLD_COOKIES", "").strip()
    if not cookies:
        raise RuntimeError(
            "MAKERWORLD_COOKIES is not set. Log in to makerworld.com in your browser, "
            "open DevTools > Network, select any request, copy the full Cookie header value, "
            "and add it to .env as: MAKERWORLD_COOKIES=bbl_csrf_token=...; ..."
        )
    return cookies


def _get_download_url(instance_id: str, dev_model_name: str) -> tuple[str, str]:
    """
    Call the MakerWorld download API and return (signed_cdn_url, filename).
    Uses curl_cffi to impersonate Chrome TLS and bypass Cloudflare.
    Requires MAKERWORLD_COOKIES to be set.
    """
    cookies = _get_cookies()

    params: dict[str, str] = {"type": "download", "fileType": ""}
    if dev_model_name:
        params["devModelName"] = dev_model_name

    resp = cffi_requests.get(
        f"{MAKERWORLD_API}/v1/design-service/instance/{instance_id}/f3mf",
        params=params,
        headers={**_CFFI_HEADERS, "Cookie": cookies},
        impersonate="chrome130",
        timeout=20,
    )

    if resp.status_code == 403:
        body = resp.text
        # Cloudflare challenge page (not yet past bot detection)
        if "<title>Just a moment" in body:
            raise RuntimeError(
                "Cloudflare blocked the download request. "
                "Ensure MAKERWORLD_COOKIES includes a valid cf_clearance cookie copied "
                "from your browser's DevTools Network tab."
            )
        try:
            msg = resp.json().get("error", "")
            if "log in" in msg.lower():
                raise RuntimeError(
                    "MakerWorld requires login to download files. "
                    "Ensure MAKERWORLD_COOKIES in .env is current — cookies expire periodically."
                )
        except (ValueError, AttributeError):
            pass
        raise RuntimeError("MakerWorld download API returned 403 — check MAKERWORLD_COOKIES in .env")

    resp.raise_for_status()
    result = resp.json()

    cdn_url = result.get("url")
    name = result.get("name") or f"model_{instance_id}.3mf"
    if not cdn_url:
        raise RuntimeError(f"MakerWorld API returned no download URL: {result}")

    return cdn_url, name


def probe() -> tuple[bool, str]:
    """
    Probe both the public metadata API and cookie availability.
    Returns (ok, message) — fails if MAKERWORLD_COOKIES is not set,
    since the probe is meant to confirm downloads will work end-to-end.
    """
    try:
        _fetch_model_meta("2462393", None)
    except Exception as e:
        return False, f"Metadata API error: {e}"

    if not os.environ.get("MAKERWORLD_COOKIES", "").strip():
        return False, "MAKERWORLD_COOKIES not set in .env — downloads require a valid browser session cookie"

    return True, "Metadata API OK, cookies configured"


def download_3mf(design_id: str, instance_id: str | None) -> tuple[str, bytes]:
    """
    Download the 3MF file for a MakerWorld model.
    Returns (filename, file_bytes).
    Requires MAKERWORLD_COOKIES to be set in the environment.
    """
    meta = _fetch_model_meta(design_id, instance_id)
    cdn_url, raw_name = _get_download_url(meta["instance_id"], meta["dev_model_name"])

    # CDN download — signed URL, no auth or Cloudflare on bblmw.com
    resp = requests.get(
        cdn_url,
        headers={"User-Agent": _META_HEADERS["User-Agent"], "Referer": MAKERWORLD_BASE + "/"},
        timeout=120,
        stream=True,
    )
    resp.raise_for_status()

    safe_name = re.sub(r'[^\w\-.]', '_', raw_name)
    if not safe_name.lower().endswith('.3mf'):
        safe_name += '.3mf'

    return safe_name, resp.content
