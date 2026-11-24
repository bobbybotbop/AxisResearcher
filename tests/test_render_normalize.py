import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from backend.render import RenderError, UnsupportedFormatError
from backend.render.normalize import ConversionError, normalize_to_render_mesh

MINIMAL_STL = b"solid x\nendsolid x\n"


@pytest.fixture(scope="module")
def box_3mf(tmp_path_factory):
    import trimesh
    path = tmp_path_factory.mktemp("meshes") / "box.3mf"
    trimesh.creation.box(extents=(10, 10, 10)).export(str(path))
    return path


@pytest.fixture(scope="module")
def box_step(tmp_path_factory):
    from conftest import make_box_step
    return make_box_step(tmp_path_factory)


def _assert_valid_stl(path):
    import trimesh
    assert str(path).lower().endswith(".stl")
    mesh = trimesh.load(str(path))
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0


def test_native_stl_passes_through_unconverted(tmp_path):
    path = tmp_path / "model.stl"
    path.write_bytes(MINIMAL_STL)
    assert normalize_to_render_mesh(path) == path


def test_3mf_converts_to_valid_stl(box_3mf):
    result = normalize_to_render_mesh(box_3mf)
    _assert_valid_stl(result)


def test_step_converts_to_valid_stl(box_step):
    result = normalize_to_render_mesh(box_step)
    _assert_valid_stl(result)


def test_stp_extension_is_supported(box_step, tmp_path):
    stp = tmp_path / "box.stp"
    stp.write_bytes(box_step.read_bytes())
    result = normalize_to_render_mesh(stp)
    _assert_valid_stl(result)


def test_amf_is_rejected_with_friendly_error(tmp_path):
    path = tmp_path / "model.amf"
    path.write_bytes(b"<amf/>")
    with pytest.raises(UnsupportedFormatError, match="not supported"):
        normalize_to_render_mesh(path)


def test_unknown_extension_is_rejected_with_friendly_error(tmp_path):
    path = tmp_path / "model.xyz"
    path.write_bytes(b"garbage")
    with pytest.raises(UnsupportedFormatError, match="not supported"):
        normalize_to_render_mesh(path)


def test_corrupt_3mf_raises_friendly_conversion_error(tmp_path):
    path = tmp_path / "broken.3mf"
    path.write_bytes(b"this is not a 3mf archive")
    with pytest.raises(ConversionError) as excinfo:
        normalize_to_render_mesh(path)
    message = str(excinfo.value)
    assert "Traceback" not in message
    assert ".3mf" in message or "convert" in message.lower()


def test_corrupt_step_raises_friendly_conversion_error(tmp_path):
    path = tmp_path / "broken.step"
    path.write_bytes(b"ISO-10303-21; not actually a step file;")
    with pytest.raises(ConversionError):
        normalize_to_render_mesh(path)


def test_conversion_errors_are_render_errors(tmp_path):
    path = tmp_path / "broken.3mf"
    path.write_bytes(b"garbage")
    with pytest.raises(RenderError):
        normalize_to_render_mesh(path)


def test_repeated_normalization_uses_cache(tmp_path, monkeypatch):
    import trimesh
    path = tmp_path / "cached_box.3mf"
    trimesh.creation.box(extents=(5, 5, 5)).export(str(path))

    import backend.render.normalize as normalize
    calls = []
    original = normalize._convert_3mf_to_stl

    def counting(src, dst):
        calls.append(src)
        return original(src, dst)

    monkeypatch.setattr(normalize, "_convert_3mf_to_stl", counting)
    first = normalize_to_render_mesh(path)
    second = normalize_to_render_mesh(path)
    assert calls == [str(path)]
    assert first == second
    assert os.path.exists(second)
