import re
import requests
from typing import Generator

THINGIVERSE_ZIP = "https://www.thingiverse.com/thing:{thing_id}/zip"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def extract_thing_id(link: str) -> str:
    """Return the numeric thing ID from a Thingiverse URL or raise ValueError."""
    match = re.search(r'thingiverse\.com/thing[:/](\d+)', link)
    if not match:
        raise ValueError(f"No Thingiverse thing ID found in: {link}")
    return match.group(1)


def stream_zip(thing_id: str) -> tuple[str, Generator[bytes, None, None]]:
    """
    Stream the zip for a Thingiverse thing.

    Returns (filename, byte_generator).
    Raises requests.HTTPError on a non-2xx response.
    """
    url = THINGIVERSE_ZIP.format(thing_id=thing_id)
    r = requests.get(url, headers=HEADERS, stream=True, timeout=60)
    r.raise_for_status()

    # Honour the server's filename if provided, else fall back.
    disp = r.headers.get("Content-Disposition", "")
    name_match = re.search(r'filename="?([^"]+)"?', disp)
    filename = name_match.group(1) if name_match else f"thing_{thing_id}.zip"

    def _gen() -> Generator[bytes, None, None]:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                yield chunk

    return filename, _gen()
