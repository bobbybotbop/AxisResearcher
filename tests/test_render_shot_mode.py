import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

import backend.db as db
import backend.copyScripts.combine_data as combine_data
from backend.constants.render import (
    DEFAULT_RENDER_SHOT_MODE,
    RENDER_ANGLE_PRESETS,
    RENDER_SHOT_MODES,
)

# The shared `config_file` fixture (tests/conftest.py) seeds a tmp axis.db with
# the minimal valid config and points the storage layer at it.


def test_shot_modes_are_single_and_multi_with_single_default():
    assert set(RENDER_SHOT_MODES) == {"single", "multi"}
    assert DEFAULT_RENDER_SHOT_MODE == "single"


def test_angle_presets_cover_the_ten_named_angles():
    assert set(RENDER_ANGLE_PRESETS) == {
        "front", "top", "left", "right", "bottom", "back",
        "front-right", "back-left", "front-top-left", "back-bottom-right",
    }


@pytest.mark.parametrize("name,azimuth,elevation", [
    ("front", 0.0, 0.0),
    ("back", 180.0, 0.0),
    ("left", -90.0, 0.0),
    ("right", 90.0, 0.0),
    ("top", 0.0, 89.0),
    ("bottom", 0.0, -89.0),
    ("front-right", 45.0, 0.0),
    ("back-left", 225.0, 0.0),
    ("front-top-left", -45.0, 45.0),
    ("back-bottom-right", 135.0, -45.0),
])
def test_angle_preset_values(name, azimuth, elevation):
    preset = RENDER_ANGLE_PRESETS[name]
    assert preset["azimuth"] == pytest.approx(azimuth)
    assert preset["elevation"] == pytest.approx(elevation)


# --- persistence seam: shot mode + rig in get/save_render_settings ---

def test_render_settings_default_to_single_shot_with_empty_rig(config_file):
    settings = combine_data.get_render_settings()
    assert settings["shot_mode"] == "single"
    assert settings["rig"] == []


def test_save_render_settings_roundtrips_shot_mode_and_rig(config_file):
    rig = [
        {"azimuth": 0.0, "elevation": 0.0},
        {"azimuth": 90.0, "elevation": 0.0},
        {"azimuth": 0.0, "elevation": 89.0},
    ]
    saved = combine_data.save_render_settings(shot_mode="multi", rig=rig)
    assert saved["shot_mode"] == "multi"
    assert saved["rig"] == rig

    reread = combine_data.get_render_settings()
    assert reread == saved

    assert db.get_preference("render_shot_mode") == "multi"
    assert db.get_preference("render_rig") == rig


def test_save_render_settings_shot_mode_partial_update_keeps_rig(config_file):
    rig = [{"azimuth": 45.0, "elevation": 0.0}]
    combine_data.save_render_settings(shot_mode="multi", rig=rig)
    combine_data.save_render_settings(color="#00ff00")
    settings = combine_data.get_render_settings()
    assert settings["shot_mode"] == "multi"
    assert settings["rig"] == rig


@pytest.mark.parametrize("kwargs", [
    {"shot_mode": "auto"},
    {"shot_mode": "Multi"},  # case-sensitive wire value
    {"shot_mode": 3},
    {"rig": "front"},
    {"rig": [{"azimuth": 0.0}]},                      # missing elevation
    {"rig": [{"azimuth": 0.0, "elevation": 0.0, "roll": 5.0}]},  # roll is fixed 0
    {"rig": [{"azimuth": "x", "elevation": 0.0}]},
    {"rig": [{"azimuth": 0.0, "elevation": 100.0}]},  # elevation out of range
    {"rig": [{"azimuth": 400.0, "elevation": 0.0}]},  # azimuth out of range
])
def test_save_render_settings_rejects_invalid_shot_mode_and_rig(config_file, kwargs):
    with pytest.raises(ValueError):
        combine_data.save_render_settings(**kwargs)
    assert combine_data.get_render_settings()["shot_mode"] == "single"


# --- HTTP seam: /api/render-settings carries shot mode + rig ---

@pytest.fixture()
def client():
    from app import app
    return app.test_client()


def test_render_settings_route_get_includes_shot_mode_and_rig(client, config_file):
    res = client.get("/api/render-settings")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["shot_mode"] == "single"
    assert payload["rig"] == []


def test_render_settings_route_post_roundtrips_shot_mode_and_rig(client, config_file):
    rig = [
        {"azimuth": 0, "elevation": 0},
        {"azimuth": 180, "elevation": 0},
        {"azimuth": 0, "elevation": 89},
    ]
    res = client.post("/api/render-settings", json={"shot_mode": "multi", "rig": rig})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["shot_mode"] == "multi"
    assert payload["rig"] == [
        {"azimuth": 0.0, "elevation": 0.0},
        {"azimuth": 180.0, "elevation": 0.0},
        {"azimuth": 0.0, "elevation": 89.0},
    ]

    reread = client.get("/api/render-settings").get_json()
    assert reread["shot_mode"] == "multi"
    assert len(reread["rig"]) == 3


def test_render_settings_route_post_rejects_invalid_shot_mode_and_rig(client, config_file):
    res = client.post("/api/render-settings", json={"shot_mode": "auto"})
    assert res.status_code == 400
    assert "shot_mode" in res.get_json()["error"].lower()

    res = client.post("/api/render-settings", json={"rig": [{"azimuth": 0}]})
    assert res.status_code == 400
    assert "rig" in res.get_json()["error"].lower() or "azimuth" in res.get_json()["error"].lower()

    assert client.get("/api/render-settings").get_json()["shot_mode"] == "single"


def test_render_profiles_pass_shot_mode_and_rig_through(client, config_file):
    rig = [{"azimuth": -45, "elevation": 45}]
    res = client.post("/api/render-profiles", json={
        "name": "three-quarter", "settings": {"shot_mode": "multi", "rig": rig, "color": "#112233"},
    })
    assert res.status_code == 201

    profiles = client.get("/api/render-profiles").get_json()["profiles"]
    assert profiles["three-quarter"]["shot_mode"] == "multi"
    assert profiles["three-quarter"]["rig"] == [{"azimuth": -45, "elevation": 45}]


# --- HTTP seam: /api/render multi-shot fan-out (NDJSON streaming) ---

import io
import time

import app as app_module

MINIMAL_STL = b"solid x\nendsolid x\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n"


@pytest.fixture()
def recording_render(tmp_path, monkeypatch):
    """Patch out Blender: record every iter_render_progress() call, write a stub PNG."""
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    calls = []

    def fake_iter_render(input_path, output_path, **kwargs):
        calls.append({"input": input_path, "output": output_path, "kwargs": kwargs})
        yield (0, 48, None)
        yield (48, 48, 1.0)
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        return output_path

    monkeypatch.setattr(app_module, "iter_render_progress", fake_iter_render)
    return calls


def _post_render(client, extra=None):
    form = {"file": (io.BytesIO(MINIMAL_STL), "model.stl")}
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


def _stream_result(client, extra=None):
    """POST /api/render and return the parsed NDJSON events."""
    res = _post_render(client, extra=extra)
    assert res.status_code == 200
    return _read_stream(res)


def _result_data(events):
    results = [e for e in events if e["type"] == "result"]
    assert len(results) == 1, "expected exactly one result event"
    return results[0]["data"]


def test_multi_shot_render_produces_one_image_per_rig_camera(client, recording_render):
    rig = [
        {"azimuth": 0, "elevation": 0},
        {"azimuth": 90, "elevation": 0},
        {"azimuth": 0, "elevation": 89},
    ]
    events = _stream_result(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    data = _result_data(events)

    # one render call per camera, in rig order, each with that camera's angles
    assert len(recording_render) == 3
    assert recording_render[0]["kwargs"]["azimuth"] == pytest.approx(0.0)
    assert recording_render[0]["kwargs"]["elevation"] == pytest.approx(0.0)
    assert recording_render[1]["kwargs"]["azimuth"] == pytest.approx(90.0)
    assert recording_render[1]["kwargs"]["elevation"] == pytest.approx(0.0)
    assert recording_render[2]["kwargs"]["azimuth"] == pytest.approx(0.0)
    assert recording_render[2]["kwargs"]["elevation"] == pytest.approx(89.0)

    # all N images returned, each fetchable
    assert len(data["images"]) == 3
    for image in data["images"]:
        assert image.startswith("/api/render-image/generated_render_")
        image_res = client.get(image)
        assert image_res.status_code == 200
        assert image_res.data == PNG_BYTES


def test_multi_shot_render_runs_cameras_sequentially(client, tmp_path, monkeypatch):
    """A second camera never starts before the previous one finished."""
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    events_order = []

    def fake_iter_render(input_path, output_path, **kwargs):
        events_order.append(("start", kwargs["azimuth"]))
        time.sleep(0.05)
        yield (48, 48, None)
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        events_order.append(("end", kwargs["azimuth"]))
        return output_path

    monkeypatch.setattr(app_module, "iter_render_progress", fake_iter_render)
    rig = [{"azimuth": 0, "elevation": 0}, {"azimuth": 90, "elevation": 0}]
    events = _stream_result(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    _result_data(events)

    assert events_order == [("start", 0.0), ("end", 0.0), ("start", 90.0), ("end", 90.0)]


def test_multi_shot_streams_per_shot_progress_events(client, recording_render):
    """Each camera start emits a 'shot i of N' progress event, in order."""
    rig = [{"azimuth": 0, "elevation": 0}, {"azimuth": 90, "elevation": 0}, {"azimuth": 180, "elevation": 0}]
    events = _stream_result(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    _result_data(events)

    shot_markers = [e for e in events if e["type"] == "progress" and "shot" in e]
    # one "shot i of N" marker per camera, plus per-sample events tagged with the shot
    starts = [e for e in shot_markers if e["status"].startswith("shot ")]
    assert [(e["shot"], e["shots"]) for e in starts] == [(1, 3), (2, 3), (3, 3)]
    # every Cycles checkpoint carries the shot index too
    sample_events = [e for e in shot_markers if e["status"].startswith("sample ")]
    assert sample_events, "expected per-sample progress within each shot"
    assert all(e["shots"] == 3 for e in sample_events)
    assert {e["shot"] for e in sample_events} == {1, 2, 3}


def test_single_shot_render_unchanged_when_shot_mode_single(client, recording_render):
    events = _stream_result(client, extra={"shot_mode": "single"})
    data = _result_data(events)
    assert len(recording_render) == 1
    # single-shot result carries the one image URL; no per-shot progress markers
    assert data["image"].startswith("/api/render-image/generated_render_")
    assert data["images"] == [data["image"]]
    assert not [e for e in events if e["type"] == "progress" and "shot" in e]


def test_render_rejects_invalid_shot_mode(client, recording_render):
    res = _post_render(client, extra={"shot_mode": "auto"})
    assert res.status_code == 400
    assert "shot_mode" in res.get_json()["error"].lower()


def test_render_rejects_malformed_rig(client, recording_render):
    res = _post_render(client, extra={"shot_mode": "multi", "rig": "not-json"})
    assert res.status_code == 400
    assert "rig" in res.get_json()["error"].lower()

    res = _post_render(client, extra={"shot_mode": "multi", "rig": json.dumps([{"azimuth": 0}])})
    assert res.status_code == 400
    assert "rig" in res.get_json()["error"].lower() or "azimuth" in res.get_json()["error"].lower()


def test_multi_shot_without_rig_falls_back_to_single_camera(client, recording_render):
    events = _stream_result(client, extra={"shot_mode": "multi"})
    data = _result_data(events)
    assert len(recording_render) == 1
    assert len(data["images"]) == 1
