import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from backend.render import (
    RenderError,
    UnsupportedFormatError,
    render_model,
)
from backend.constants.render import (
    DEFAULT_RENDER_COLOR,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_ROUGHNESS,
    NATIVE_RENDER_EXTENSIONS,
)


def test_native_extensions_cover_stl_obj_ply():
    assert ".stl" in NATIVE_RENDER_EXTENSIONS
    assert ".obj" in NATIVE_RENDER_EXTENSIONS
    assert ".ply" in NATIVE_RENDER_EXTENSIONS


def test_defaults_match_spec():
    assert DEFAULT_RENDER_COLOR == "#1a1a1a"
    assert DEFAULT_RENDER_ROUGHNESS == pytest.approx(0.3)
    assert DEFAULT_RENDER_RESOLUTION == 1024


def test_missing_blender_raises_friendly_error(tmp_path):
    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    with pytest.raises(RenderError, match="[Bb]lender"):
        render_model(
            mesh,
            tmp_path / "out.png",
            blender_path=str(tmp_path / "no-such-blender.exe"),
        )


def test_unsupported_extension_rejected(tmp_path):
    mesh = tmp_path / "model.amf"
    mesh.write_text("<amf/>")
    with pytest.raises(UnsupportedFormatError, match="\\.amf"):
        render_model(mesh, tmp_path / "out.png")
