import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import zipfile

import pytest

from backend.constants.files_3d import PREFERRED_3D_EXTENSIONS
from backend.downloaders.zip_utils import extract_best_3d_file


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_amf_not_in_preferred_extensions():
    assert ".amf" not in PREFERRED_3D_EXTENSIONS


def test_zip_with_only_amf_is_rejected_with_clear_message():
    zip_bytes = make_zip({"model.amf": b"fake-amf-data"})
    with pytest.raises(ValueError) as excinfo:
        extract_best_3d_file(zip_bytes)
    message = str(excinfo.value)
    assert ".amf" in message
    assert "not supported" in message


def test_zip_with_amf_and_supported_file_picks_supported_file():
    zip_bytes = make_zip({
        "model.amf": b"fake-amf-data",
        "model.stl": b"fake-stl-data",
    })
    filename, data = extract_best_3d_file(zip_bytes)
    assert filename == "model.stl"
    assert data == b"fake-stl-data"


def test_zip_with_supported_file_still_works():
    zip_bytes = make_zip({
        "readme.txt": b"hello",
        "part.3mf": b"fake-3mf-data",
    })
    filename, data = extract_best_3d_file(zip_bytes)
    assert filename == "part.3mf"
    assert data == b"fake-3mf-data"


def test_zip_without_any_3d_file_lists_supported_formats():
    zip_bytes = make_zip({"readme.txt": b"hello"})
    with pytest.raises(ValueError) as excinfo:
        extract_best_3d_file(zip_bytes)
    assert "No supported 3D file" in str(excinfo.value)
