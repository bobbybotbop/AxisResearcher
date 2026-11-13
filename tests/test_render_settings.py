import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json

import pytest

import backend.copyScripts.combine_data as combine_data
from app import app

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


@pytest.fixture()
def client():
    return app.test_client()


# --- persistence seam: get_render_settings / save_render_settings ---

def test_get_render_settings_returns_spec_defaults(config_file):
    settings = combine_data.get_render_settings()
    assert settings == {
        "color": "#1a1a1a",
        "roughness": pytest.approx(0.3),
        "resolution": 1024,
        "fov": pytest.approx(40),
    }


def test_render_settings_schema_has_no_camera_keys(config_file):
    # Camera angle/target stay ephemeral (spec); only color/roughness/resolution/fov persist
    assert set(combine_data.get_render_settings()) == {"color", "roughness", "resolution", "fov"}


def test_save_render_settings_roundtrip(config_file):
    saved = combine_data.save_render_settings(color="#FF0000", roughness=0.8, resolution=512, fov=60)
    assert saved["color"] == "#ff0000"
    assert saved["roughness"] == pytest.approx(0.8)
    assert saved["resolution"] == 512
    assert saved["fov"] == pytest.approx(60)

    reread = combine_data.get_render_settings()
    assert reread == saved

    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["render_color"] == "#ff0000"
    assert on_disk["render_roughness"] == pytest.approx(0.8)
    assert on_disk["render_resolution"] == 512
    assert on_disk["render_fov"] == pytest.approx(60)


def test_save_render_settings_partial_update(config_file):
    combine_data.save_render_settings(resolution=2048)
    combine_data.save_render_settings(color="#00ff00")
    settings = combine_data.get_render_settings()
    assert settings["color"] == "#00ff00"
    assert settings["resolution"] == 2048
    assert settings["roughness"] == pytest.approx(0.3)  # untouched default
    assert settings["fov"] == pytest.approx(40)


@pytest.mark.parametrize("kwargs", [
    {"color": "red"},
    {"color": "#12345"},
    {"roughness": -0.1},
    {"roughness": 1.5},
    {"resolution": 1000},
    {"resolution": "abc"},
    {"fov": 10},
    {"fov": 90},
])
def test_save_render_settings_rejects_invalid_values(config_file, kwargs):
    with pytest.raises(ValueError):
        combine_data.save_render_settings(**kwargs)
    # nothing was written
    assert combine_data.get_render_settings()["color"] == "#1a1a1a"


# --- HTTP seam: /api/render-settings ---

def test_render_settings_route_get_defaults(client, config_file):
    res = client.get("/api/render-settings")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["color"] == "#1a1a1a"
    assert payload["roughness"] == pytest.approx(0.3)
    assert payload["resolution"] == 1024
    assert payload["fov"] == pytest.approx(40)


def test_render_settings_route_post_persists(client, config_file):
    res = client.post("/api/render-settings", json={"color": "#3366cc", "resolution": 2048})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["color"] == "#3366cc"
    assert payload["resolution"] == 2048

    # persists across reads (simulating a panel reopen / page reload)
    reread = client.get("/api/render-settings").get_json()
    assert reread["color"] == "#3366cc"
    assert reread["resolution"] == 2048


def test_render_settings_route_post_rejects_invalid(client, config_file):
    res = client.post("/api/render-settings", json={"color": "not-a-color"})
    assert res.status_code == 400
    assert "color" in res.get_json()["error"].lower()

    res = client.post("/api/render-settings", json={"resolution": 768})
    assert res.status_code == 400

    # rejected writes did not stick
    assert client.get("/api/render-settings").get_json()["color"] == "#1a1a1a"
