import io
import re
import zipfile
import requests

GRAPHQL_URL = "https://api.printables.com/graphql/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
}

LIST_FILES_QUERY = """
query ModelFiles($id: ID!) {
  print(id: $id) {
    id
    name
    stls { id name fileSize }
    gcodes { id name fileSize }
    slas { id name fileSize }
  }
}
"""

GET_DOWNLOAD_LINK_MUTATION = """
mutation GetDownloadLink($id: ID!, $printId: ID!, $fileType: DownloadFileTypeEnum!, $source: DownloadSourceEnum!) {
  getDownloadLink(id: $id, printId: $printId, fileType: $fileType, source: $source) {
    ok
    errors { field messages }
    output { link count ttl }
  }
}
"""


def extract_model_id(link: str) -> str:
    """Return the numeric model ID from a Printables URL or raise ValueError."""
    match = re.search(r'/model/(\d+)', link)
    if not match:
        raise ValueError(f"No Printables model ID found in: {link}")
    return match.group(1)


def _gql(query: str, variables: dict) -> dict:
    """Execute a GraphQL request and raise on HTTP or GraphQL errors."""
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def _list_files(model_id: str) -> tuple[str, list[dict]]:
    """
    Return (model_name, file_list) where each file is
    {"id": str, "name": str, "file_type": str}.
    Only STL, GCode, and SLA files are included.
    """
    data = _gql(LIST_FILES_QUERY, {"id": model_id})["print"]
    model_name = data.get("name", f"printables_{model_id}")
    files = []
    for kind, file_type in [("stls", "stl"), ("gcodes", "gcode"), ("slas", "sla")]:
        for f in data.get(kind) or []:
            files.append({"id": f["id"], "name": f["name"], "file_type": file_type})
    return model_name, files


def _get_download_link(file_id: str, model_id: str, file_type: str) -> str:
    """Return a temporary signed download URL for one file."""
    result = _gql(GET_DOWNLOAD_LINK_MUTATION, {
        "id": file_id,
        "printId": model_id,
        "fileType": file_type,
        "source": "model_detail",
    })["getDownloadLink"]
    if not result.get("ok"):
        errors = result.get("errors", [])
        raise RuntimeError(f"getDownloadLink failed: {errors}")
    return result["output"]["link"]


def build_zip(model_id: str) -> tuple[str, bytes]:
    """
    Download all STL/GCode/SLA files for a Printables model and bundle them
    into an in-memory zip.

    Returns (zip_filename, zip_bytes).
    """
    model_name, files = _list_files(model_id)
    if not files:
        raise ValueError(f"No downloadable files found for model {model_id}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            try:
                url = _get_download_link(f["id"], model_id, f["file_type"])
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                zf.writestr(f["name"], r.content)
            except Exception as e:
                # Skip files that can't be downloaded rather than aborting the whole zip.
                print(f"[printables] skipping {f['name']}: {e}")

    zip_bytes = buf.getvalue()
    safe_name = re.sub(r'[^\w\-.]', '_', model_name)
    return f"{safe_name}.zip", zip_bytes
