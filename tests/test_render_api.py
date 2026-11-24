import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import io
import json

import pytest

import app as app_module
from app import app

MINIMAL_STL = b"solid x\nendsolid x\n"
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"  # enough for the route tests; pixel checks live in test_render_studio.py
)


@pytest.fixture()
def client():
    return app.test_client()


@pytest.fixture()
def fake_render(tmp_path, monkeypatch):
    """Patch out Blender: iter_render_progress yields checkpoints, writes a stub PNG."""
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    calls = {}

    def fake_iter_render(input_path, output_path, **kwargs):
        calls["input"] = input_path
        calls["kwargs"] = kwargs
        yield (0, 48, None)
        yield (48, 48, 1.0)
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        return output_path

    monkeypatch.setattr(app_module, "iter_render_progress", fake_iter_render)
    return calls


def _post_render(client, filename="model.stl", data=MINIMAL_STL, extra=None):
    form = {"file": (io.BytesIO(data), filename)}
    if extra:
        form.update(extra)
    return client.post("/api/render", data=form, content_type="multipart/form-data")


def _read_stream(res):
    """Parse a streaming NDJSON response into a list of events."""
    events = []
    for line in res.response:
        line = line.decode("utf-8") if isinstance(line, bytes) else line
        if line.strip():
            events.append(json.loads(line))
    return events


def _stream_result(client, **kwargs):
    """POST /api/render and return the parsed NDJSON events."""
    res = _post_render(client, **kwargs)
    assert res.status_code == 200
    return _read_stream(res)


def test_render_requires_a_file(client):
    res = client.post("/api/render", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "file" in res.get_json()["error"].lower()


def test_render_rejects_unsupported_format(client):
    res = _post_render(client, filename="model.amf", data=b"<amf/>")
    assert res.status_code == 400
    error = res.get_json()["error"].lower()
    assert "not supported" in error or ".amf" in error


def test_render_rejects_bad_resolution(client, fake_render):
    res = _post_render(client, extra={"resolution": "1000"})
    assert res.status_code == 400
    assert "resolution" in res.get_json()["error"].lower()


def test_render_streams_progress_then_result(client, fake_render):
    events = _stream_result(client, extra={"color": "#1a1a1a", "roughness": "0.3", "resolution": "1024"})

    progress = [e for e in events if e["type"] == "progress"]
    assert progress, "expected live progress events before the result"
    assert any(e.get("current") == 48 and e.get("total") == 48 for e in progress)

    result = [e for e in events if e["type"] == "result"]
    assert len(result) == 1
    data = result[0]["data"]
    assert data["image"].startswith("/api/render-image/generated_render_")
    assert data["image"].endswith(".png")
    assert data["filename"].endswith(".png")

    # settings were forwarded to the renderer
    assert fake_render["kwargs"]["color"] == "#1a1a1a"
    assert fake_render["kwargs"]["roughness"] == pytest.approx(0.3)
    assert fake_render["kwargs"]["resolution"] == 1024

    image_res = client.get(data["image"])
    assert image_res.status_code == 200
    assert image_res.mimetype == "image/png"
    assert image_res.data == PNG_BYTES


def test_render_result_event_carries_image_and_filename(client, fake_render):
    events = _stream_result(client)
    result = [e for e in events if e["type"] == "result"][0]["data"]
    assert result["image"] == f"/api/render-image/{result['filename']}"
    # single-shot: images list carries exactly the one image
    assert result["images"] == [result["image"]]


def test_render_forwards_expanded_settings(client, fake_render):
    """Lighting/shadow/exposure/finish form fields reach the renderer."""
    events = _stream_result(client, extra={
        "key_energy": "300", "fill_energy": "20", "rim_energy": "500",
        "ambient": "0.8", "shadow": "false", "shadow_softness": "3.0",
        "exposure": "1.5",
        "finish": "layer-lines", "layer_height_mm": "0.12", "layer_depth": "0.7",
    })
    assert [e for e in events if e["type"] == "result"]

    kwargs = fake_render["kwargs"]
    assert kwargs["key_energy"] == pytest.approx(300)
    assert kwargs["fill_energy"] == pytest.approx(20)
    assert kwargs["rim_energy"] == pytest.approx(500)
    assert kwargs["ambient"] == pytest.approx(0.8)
    assert kwargs["shadow"] is False
    assert kwargs["shadow_softness"] == pytest.approx(3.0)
    assert kwargs["exposure"] == pytest.approx(1.5)
    assert kwargs["finish"] == "layer-lines"
    assert kwargs["layer_height_mm"] == pytest.approx(0.12)
    assert kwargs["layer_depth"] == pytest.approx(0.7)


def test_render_defaults_forward_spec_values(client, fake_render):
    """A bare render request forwards defaults that reproduce today's render."""
    events = _stream_result(client)
    assert [e for e in events if e["type"] == "result"]

    kwargs = fake_render["kwargs"]
    assert kwargs["key_energy"] == pytest.approx(150)
    assert kwargs["fill_energy"] == pytest.approx(60)
    assert kwargs["rim_energy"] == pytest.approx(250)
    assert kwargs["ambient"] == pytest.approx(0.35)
    assert kwargs["shadow"] is True
    assert kwargs["shadow_softness"] == pytest.approx(1.5)
    assert kwargs["exposure"] == pytest.approx(1.0)
    assert kwargs["finish"] == "smooth"
    assert kwargs["layer_height_mm"] == pytest.approx(0.2)
    assert kwargs["layer_depth"] == pytest.approx(0.4)


def test_render_rejects_invalid_expanded_settings(client, fake_render):
    res = _post_render(client, extra={"finish": "matte"})
    assert res.status_code == 400
    assert "finish" in res.get_json()["error"].lower()

    res = _post_render(client, extra={"exposure": "10"})
    assert res.status_code == 400

    res = _post_render(client, extra={"shadow": "maybe"})
    assert res.status_code == 400


def test_render_failure_surfaces_friendly_error_event(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))

    def broken_render(input_path, output_path, **kwargs):
        from backend.render import BlenderNotFoundError
        raise BlenderNotFoundError("Blender was not found. Set the BLENDER_PATH environment variable.")
        yield  # make it a generator so the endpoint's next() triggers the raise

    monkeypatch.setattr(app_module, "iter_render_progress", broken_render)
    events = _stream_result(client)
    errors = [e for e in events if e["type"] == "error"]
    assert len(errors) == 1
    assert "Blender" in errors[0]["error"]
    assert not [e for e in events if e["type"] == "result"]


def test_render_without_camera_uses_default_angle(client, fake_render):
    _stream_result(client)
    assert fake_render["kwargs"]["azimuth"] == pytest.approx(45.0)
    assert fake_render["kwargs"]["elevation"] == pytest.approx(28.0)
    assert fake_render["kwargs"]["fov"] == pytest.approx(40.0)


def test_render_forwards_camera_intent_as_blender_angles(client, fake_render):
    # three.js (Y-up) camera 5 along +Z looking at the origin is azimuth -90
    # in Blender (Z-up) coordinates — see tests/test_camera_intent.py
    events = _stream_result(client, extra={
        "camera_position": "0,0,5",
        "camera_target": "0,0,0",
        "fov": "55",
    })
    assert [e for e in events if e["type"] == "result"]
    assert fake_render["kwargs"]["azimuth"] == pytest.approx(-90.0)
    assert fake_render["kwargs"]["elevation"] == pytest.approx(0.0, abs=1e-6)
    assert fake_render["kwargs"]["fov"] == pytest.approx(55.0)


def test_render_rejects_fov_outside_slider_range(client, fake_render):
    res = _post_render(client, extra={"fov": "10"})
    assert res.status_code == 400
    assert "fov" in res.get_json()["error"].lower()
    res = _post_render(client, extra={"fov": "90"})
    assert res.status_code == 400
    assert "fov" in res.get_json()["error"].lower()


def test_render_rejects_non_numeric_fov(client, fake_render):
    res = _post_render(client, extra={"fov": "wide"})
    assert res.status_code == 400
    assert "fov" in res.get_json()["error"].lower()


def test_render_rejects_malformed_camera_position(client, fake_render):
    res = _post_render(client, extra={"camera_position": "1,2", "camera_target": "0,0,0"})
    assert res.status_code == 400
    assert "camera" in res.get_json()["error"].lower()
    res = _post_render(client, extra={"camera_position": "a,b,c", "camera_target": "0,0,0"})
    assert res.status_code == 400
    assert "camera" in res.get_json()["error"].lower()


def test_render_rejects_camera_position_without_target(client, fake_render):
    res = _post_render(client, extra={"camera_position": "0,0,5"})
    assert res.status_code == 400
    assert "camera" in res.get_json()["error"].lower()


def test_render_rejects_degenerate_camera_at_target(client, fake_render):
    res = _post_render(client, extra={"camera_position": "1,1,1", "camera_target": "1,1,1"})
    assert res.status_code == 400
    assert "camera" in res.get_json()["error"].lower()


def test_render_image_rejects_bad_filename(client):
    res = client.get("/api/render-image/..%2F..%2Fapp.py")
    assert res.status_code in (400, 404)
    res = client.get("/api/render-image/evil.png")
    assert res.status_code == 400


@pytest.fixture(scope="module")
def box_3mf_bytes():
    import trimesh
    return trimesh.creation.box(extents=(10, 10, 10)).export(file_type="3mf")


@pytest.fixture(scope="module")
def box_step_bytes(tmp_path_factory):
    from conftest import make_box_step
    return make_box_step(tmp_path_factory).read_bytes()


def test_render_accepts_3mf_and_renders_the_converted_stl(client, fake_render, box_3mf_bytes):
    events = _stream_result(client, filename="model.3mf", data=box_3mf_bytes)
    assert [e for e in events if e["type"] == "result"]
    # Blender only ever sees the normalized Render Mesh
    assert str(fake_render["input"]).lower().endswith(".stl")


def test_render_accepts_step_and_renders_the_converted_stl(client, fake_render, box_step_bytes):
    events = _stream_result(client, filename="model.step", data=box_step_bytes)
    assert [e for e in events if e["type"] == "result"]
    assert str(fake_render["input"]).lower().endswith(".stl")


def test_preview_then_render_converts_only_once(client, fake_render, tmp_path, monkeypatch):
    import trimesh
    import backend.render.normalize as normalize

    data = trimesh.creation.box(extents=(7, 7, 7)).export(file_type="3mf")
    calls = []
    original = normalize._convert_3mf_to_stl

    def counting(src, dst):
        calls.append(src)
        return original(src, dst)

    monkeypatch.setattr(normalize, "_convert_3mf_to_stl", counting)

    preview_res = client.post(
        "/api/render-preview",
        data={"file": (io.BytesIO(data), "model.3mf")},
        content_type="multipart/form-data",
    )
    assert preview_res.status_code == 200

    render_res = _post_render(client, filename="model.3mf", data=data)
    assert render_res.status_code == 200
    events = _read_stream(render_res)
    assert [e for e in events if e["type"] == "result"]
    assert len(calls) == 1


def test_render_corrupt_3mf_fails_with_friendly_error(client, fake_render):
    events = _stream_result(client, filename="model.3mf", data=b"not a real archive")
    errors = [e for e in events if e["type"] == "error"]
    assert len(errors) == 1
    assert "Traceback" not in errors[0]["error"]
