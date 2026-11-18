import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

import backend.copyScripts.combine_data as combine_data
from backend.constants.render import (
    DEFAULT_RENDER_SHOT_MODE,
    RENDER_ANGLE_PRESETS,
    RENDER_SHOT_MODES,
)

# Minimal config satisfying load_config()'s required keys
BASE_CONFIG = {
    "counter": 1,
    "merchant_location_key": "TestLocation",
    "default_quantity": 1,
    "default_dimensions": {"length": "1", "width": "1", "height": "1", "unit": "INCH"},
    "default_weight": {"value": "1", "unit": "POUND"},
}


@pytest.fixture()
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "listingPreferences.json"
    path.write_text(json.dumps(BASE_CONFIG), encoding="utf-8")
    monkeypatch.setattr(combine_data, "CONFIG_FILE", str(path))
    return path


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

    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["render_shot_mode"] == "multi"
    assert on_disk["render_rig"] == rig


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


# --- HTTP seam: /api/render multi-shot fan-out ---

import io
import threading
import time

import app as app_module

MINIMAL_STL = b"solid x\nendsolid x\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n"


@pytest.fixture()
def recording_render(tmp_path, monkeypatch):
    """Patch out Blender: record every render_model() call, write a stub PNG."""
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    calls = []

    def fake_render_model(input_path, output_path, **kwargs):
        calls.append({"input": input_path, "output": output_path, "kwargs": kwargs})
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        return output_path

    monkeypatch.setattr(app_module, "render_model", fake_render_model)
    return calls


def _post_render(client, extra=None):
    form = {"file": (io.BytesIO(MINIMAL_STL), "model.stl")}
    if extra:
        form.update(extra)
    return client.post("/api/render", data=form, content_type="multipart/form-data")


def _wait_for_status(client, task_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/api/render-status/{task_id}")
        assert res.status_code == 200
        payload = res.get_json()
        if payload["status"] in ("completed", "failed"):
            return payload
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not finish in {timeout}s")


def test_multi_shot_render_produces_one_image_per_rig_camera(client, recording_render):
    rig = [
        {"azimuth": 0, "elevation": 0},
        {"azimuth": 90, "elevation": 0},
        {"azimuth": 0, "elevation": 89},
    ]
    res = _post_render(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    assert res.status_code == 200
    payload = _wait_for_status(client, res.get_json()["task_id"])
    assert payload["status"] == "completed"

    # one render_model() call per camera, in rig order, each with that camera's angles
    assert len(recording_render) == 3
    assert recording_render[0]["kwargs"]["azimuth"] == pytest.approx(0.0)
    assert recording_render[0]["kwargs"]["elevation"] == pytest.approx(0.0)
    assert recording_render[1]["kwargs"]["azimuth"] == pytest.approx(90.0)
    assert recording_render[1]["kwargs"]["elevation"] == pytest.approx(0.0)
    assert recording_render[2]["kwargs"]["azimuth"] == pytest.approx(0.0)
    assert recording_render[2]["kwargs"]["elevation"] == pytest.approx(89.0)

    # all N images returned, each fetchable
    assert len(payload["images"]) == 3
    for image in payload["images"]:
        assert image.startswith("/api/render-image/generated_render_")
        image_res = client.get(image)
        assert image_res.status_code == 200
        assert image_res.data == PNG_BYTES


def test_multi_shot_render_runs_cameras_sequentially(client, tmp_path, monkeypatch):
    """A second camera never starts before the previous one finished."""
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    events = []

    def fake_render_model(input_path, output_path, **kwargs):
        events.append(("start", kwargs["azimuth"]))
        time.sleep(0.05)
        events.append(("end", kwargs["azimuth"]))
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        return output_path

    monkeypatch.setattr(app_module, "render_model", fake_render_model)
    rig = [{"azimuth": 0, "elevation": 0}, {"azimuth": 90, "elevation": 0}]
    res = _post_render(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    assert res.status_code == 200
    payload = _wait_for_status(client, res.get_json()["task_id"])
    assert payload["status"] == "completed"

    assert events == [("start", 0.0), ("end", 0.0), ("start", 90.0), ("end", 90.0)]


def test_multi_shot_status_reports_progress_and_completed_images(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "GENERATED_IMAGES_DIR", str(tmp_path))
    first_returned = threading.Event()
    release_second = threading.Event()

    def fake_render_model(input_path, output_path, **kwargs):
        with open(output_path, "wb") as f:
            f.write(PNG_BYTES)
        if kwargs["azimuth"] == 0.0:
            first_returned.set()
        else:
            # hold the second camera until the mid-render status was observed
            release_second.wait(5)
        return output_path

    monkeypatch.setattr(app_module, "render_model", fake_render_model)
    rig = [{"azimuth": 0, "elevation": 0}, {"azimuth": 90, "elevation": 0}]
    res = _post_render(client, extra={"shot_mode": "multi", "rig": json.dumps(rig)})
    task_id = res.get_json()["task_id"]

    assert first_returned.wait(5)
    # the worker records shot 1 just after render_model returns; poll until it lands
    deadline = time.time() + 5
    while True:
        mid = client.get(f"/api/render-status/{task_id}").get_json()
        if mid["shots_completed"] == 1:
            break
        assert time.time() < deadline, "first shot was never recorded"
        time.sleep(0.02)
    release_second.set()
    final = _wait_for_status(client, task_id)

    assert mid["status"] == "running"
    assert mid["shots_completed"] == 1
    assert mid["shots_total"] == 2
    assert len(mid["images"]) == 1
    assert final["status"] == "completed"
    assert final["shots_completed"] == 2
    assert len(final["images"]) == 2


def test_single_shot_render_unchanged_when_shot_mode_single(client, recording_render):
    res = _post_render(client, extra={"shot_mode": "single"})
    assert res.status_code == 200
    payload = _wait_for_status(client, res.get_json()["task_id"])
    assert payload["status"] == "completed"
    assert len(recording_render) == 1
    # single-shot payload shape is unchanged: one image URL, no images list
    assert payload["image"].startswith("/api/render-image/generated_render_")
    assert "images" not in payload


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
    res = _post_render(client, extra={"shot_mode": "multi"})
    assert res.status_code == 200
    payload = _wait_for_status(client, res.get_json()["task_id"])
    assert payload["status"] == "completed"
    assert len(recording_render) == 1
    assert len(payload["images"]) == 1
