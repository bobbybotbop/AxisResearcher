import io
import json
import re
import time
import urllib.parse
import zipfile

from curl_cffi import requests as cffi_requests

THANGS_BASE = "https://thangs.com"


class PaidModelError(ValueError):
    """Raised when the requested model requires a paid plan or membership."""


def extract_model_id(link: str) -> str:
    """Return the numeric model ID from a Thangs URL or raise ValueError."""
    match = re.search(r"-(\d+)(?:[/?#].*)?$", link)
    if not match:
        raise ValueError(f"No Thangs model ID found in: {link}")
    return match.group(1)


def _make_session() -> cffi_requests.Session:
    return cffi_requests.Session(impersonate="chrome131")


def _fetch_model_data(session: cffi_requests.Session, link: str) -> dict:
    """
    Fetch the model page and return the model data dict from __NEXT_DATA__.
    Raises RuntimeError if the page cannot be parsed or the model is not found.
    """
    r = session.get(link, timeout=30)
    r.raise_for_status()

    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL
    )
    if not match:
        raise RuntimeError("Could not find __NEXT_DATA__ in the Thangs page — the site layout may have changed.")

    try:
        page_data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse __NEXT_DATA__: {e}") from e

    try:
        model = page_data["props"]["pageProps"]["initialState"]["model"]["data"]
    except (KeyError, TypeError):
        raise RuntimeError(
            "Could not locate model data in the Thangs page. "
            "The model may require login or the URL may be invalid."
        )

    if not model:
        raise RuntimeError("Model data is empty — the model may not exist or require login.")

    return model


def _check_access(model: dict) -> None:
    """Raise PaidModelError if the model is not freely downloadable."""
    if model.get("isPaid") or model.get("accessTypeId", 0) != 0:
        name = model.get("name", "this model")
        raise PaidModelError(
            f"Paid model — '{name}' requires a paid plan or membership and cannot be downloaded for free."
        )


def _download_part(session: cffi_requests.Session, model_id: str, filename: str, referer: str) -> bytes:
    """Download one model part via the viewerFile redirect API."""
    url = (
        f"{THANGS_BASE}/api/v4/models/{model_id}/viewerFile"
        f"?part={urllib.parse.quote(filename)}&useDraco=false"
    )
    r = session.get(url, headers={"Accept": "*/*", "Referer": referer}, timeout=120)
    r.raise_for_status()
    return r.content


def probe() -> tuple[bool, str]:
    """
    Quick connectivity probe: call the plans API for a known public model.
    Returns (ok, message).
    """
    probe_model_id = "1412046"
    try:
        session = _make_session()
        r = session.get(
            f"{THANGS_BASE}/api/v4/models/{probe_model_id}/plans",
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            return True, f"Thangs API accessible (model {probe_model_id})"
        return False, f"Unexpected response: HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def build_zip(link: str, file_download_delay: float = 0.0) -> tuple[str, bytes]:
    """
    Download all model parts for a free Thangs model and bundle them into
    an in-memory zip.

    Returns (zip_filename, zip_bytes).
    Raises PaidModelError for models that require payment/membership.
    """
    model_id = extract_model_id(link)
    session = _make_session()
    model = _fetch_model_data(session, link)

    _check_access(model)

    model_name = model.get("name") or f"thangs_{model_id}"
    parts = model.get("parts") or []
    if not parts:
        raise RuntimeError(f"No downloadable parts found for Thangs model {model_id}.")

    buf = io.BytesIO()
    succeeded = 0
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, part in enumerate(parts):
            if i > 0 and file_download_delay > 0:
                time.sleep(file_download_delay)
            part_name = part.get("name") or f"part_{i}"
            part_filename = part.get("filename", "")
            if not part_filename:
                print(f"[thangs] skipping {part_name}: no filename")
                continue
            try:
                content = _download_part(session, model_id, part_filename, referer=link)
                zf.writestr(part_name, content)
                succeeded += 1
            except Exception as e:
                print(f"[thangs] skipping {part_name}: {e}")

    if succeeded == 0:
        raise RuntimeError(f"All {len(parts)} parts failed to download for Thangs model {model_id}.")

    safe_name = re.sub(r"[^\w\-.]", "_", model_name)
    return f"{safe_name}.zip", buf.getvalue()
