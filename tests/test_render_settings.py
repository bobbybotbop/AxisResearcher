import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

import backend.db as db
import backend.copyScripts.combine_data as combine_data
from app import app

# The shared `config_file` fixture (tests/conftest.py) seeds a tmp axis.db with
# the minimal valid config and points the storage layer at it.


@pytest.fixture()
def client():
    return app.test_client()


# --- persistence seam: get_render_settings / save_render_settings ---

SPEC_DEFAULTS = {
    "color": "#0d0d0d",
    "roughness": 0.3,
    "resolution": 1024,
    "fov": 40,
    "finish": "smooth",
    "layer_height_mm": 0.2,
    "layer_depth": 0.4,
    "key_energy": 150.0,
    "fill_energy": 60.0,
    "rim_energy": 250.0,
    "ambient": 0.35,
    "shadow": True,
    "shadow_softness": 1.5,
    "exposure": 1.0,
    "shot_mode": "single",
    "rig": [],
}


def test_get_render_settings_returns_spec_defaults(config_file):
    settings = combine_data.get_render_settings()
    for key, expected in SPEC_DEFAULTS.items():
        actual = settings[key]
        assert actual == (pytest.approx(expected) if isinstance(expected, float) else expected), key


def test_render_settings_schema_has_no_camera_keys(config_file):
    # Camera angle/target stay ephemeral (spec); the persisted schema is the
    # full Render Settings surface: material, lighting, shadows, exposure, fov,
    # plus Shot Mode and its Camera Rig.
    assert set(combine_data.get_render_settings()) == set(SPEC_DEFAULTS)


def test_save_render_settings_roundtrip(config_file):
    saved = combine_data.save_render_settings(color="#FF0000", roughness=0.8, resolution=512, fov=60)
    assert saved["color"] == "#ff0000"
    assert saved["roughness"] == pytest.approx(0.8)
    assert saved["resolution"] == 512
    assert saved["fov"] == pytest.approx(60)

    reread = combine_data.get_render_settings()
    assert reread == saved

    assert db.get_preference("render_color") == "#ff0000"
    assert db.get_preference("render_roughness") == pytest.approx(0.8)
    assert db.get_preference("render_resolution") == 512
    assert db.get_preference("render_fov") == pytest.approx(60)


def test_save_render_settings_partial_update(config_file):
    combine_data.save_render_settings(resolution=2048)
    combine_data.save_render_settings(color="#00ff00")
    settings = combine_data.get_render_settings()
    assert settings["color"] == "#00ff00"
    assert settings["resolution"] == 2048
    assert settings["roughness"] == pytest.approx(0.3)  # untouched default
    assert settings["fov"] == pytest.approx(40)


def test_save_render_settings_roundtrips_new_fields(config_file):
    saved = combine_data.save_render_settings(
        finish="layer-lines", layer_height_mm=0.12, layer_depth=0.7,
        key_energy=300, fill_energy=20, rim_energy=500,
        ambient=0.8, shadow=False, shadow_softness=3.0, exposure=1.5,
    )
    assert saved["finish"] == "layer-lines"
    assert saved["layer_height_mm"] == pytest.approx(0.12)
    assert saved["layer_depth"] == pytest.approx(0.7)
    assert saved["key_energy"] == pytest.approx(300)
    assert saved["fill_energy"] == pytest.approx(20)
    assert saved["rim_energy"] == pytest.approx(500)
    assert saved["ambient"] == pytest.approx(0.8)
    assert saved["shadow"] is False
    assert saved["shadow_softness"] == pytest.approx(3.0)
    assert saved["exposure"] == pytest.approx(1.5)

    reread = combine_data.get_render_settings()
    assert reread == saved

    assert db.get_preference("render_finish") == "layer-lines"
    assert db.get_preference("render_key_energy") == pytest.approx(300)
    assert db.get_preference("render_shadow") is False
    assert db.get_preference("render_exposure") == pytest.approx(1.5)


@pytest.mark.parametrize("kwargs", [
    {"finish": "matte"},
    {"finish": "Layer-Lines"},  # case-sensitive wire value
    {"layer_height_mm": 0.05},
    {"layer_height_mm": 0.5},
    {"layer_depth": -0.1},
    {"layer_depth": 1.5},
    {"key_energy": -1},
    {"key_energy": 5000},
    {"fill_energy": -1},
    {"rim_energy": -1},
    {"ambient": -0.1},
    {"ambient": 3.0},
    {"shadow_softness": 0},
    {"shadow_softness": 20},
    {"exposure": 0},
    {"exposure": 5},
])
def test_save_render_settings_rejects_invalid_new_values(config_file, kwargs):
    with pytest.raises(ValueError):
        combine_data.save_render_settings(**kwargs)
    # nothing was written
    assert combine_data.get_render_settings()["finish"] == "smooth"


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
    assert combine_data.get_render_settings()["color"] == "#0d0d0d"


# --- HTTP seam: /api/render-settings ---

def test_render_settings_route_get_defaults(client, config_file):
    res = client.get("/api/render-settings")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["color"] == "#0d0d0d"
    assert payload["roughness"] == pytest.approx(0.3)
    assert payload["resolution"] == 1024
    assert payload["fov"] == pytest.approx(40)
    # expanded surface: lighting, shadows, exposure, finish
    assert payload["key_energy"] == pytest.approx(150)
    assert payload["fill_energy"] == pytest.approx(60)
    assert payload["rim_energy"] == pytest.approx(250)
    assert payload["ambient"] == pytest.approx(0.35)
    assert payload["shadow"] is True
    assert payload["shadow_softness"] == pytest.approx(1.5)
    assert payload["exposure"] == pytest.approx(1.0)
    assert payload["finish"] == "smooth"
    assert payload["layer_height_mm"] == pytest.approx(0.2)
    assert payload["layer_depth"] == pytest.approx(0.4)


def test_render_settings_route_post_roundtrips_new_fields(client, config_file):
    res = client.post("/api/render-settings", json={
        "key_energy": 300, "ambient": 0.8, "shadow": False,
        "shadow_softness": 3.0, "exposure": 1.5,
        "finish": "layer-lines", "layer_height_mm": 0.12, "layer_depth": 0.7,
    })
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["key_energy"] == pytest.approx(300)
    assert payload["ambient"] == pytest.approx(0.8)
    assert payload["shadow"] is False
    assert payload["shadow_softness"] == pytest.approx(3.0)
    assert payload["exposure"] == pytest.approx(1.5)
    assert payload["finish"] == "layer-lines"
    assert payload["layer_height_mm"] == pytest.approx(0.12)
    assert payload["layer_depth"] == pytest.approx(0.7)

    # persists across reads (simulating a panel reopen / page reload)
    reread = client.get("/api/render-settings").get_json()
    assert reread["key_energy"] == pytest.approx(300)
    assert reread["shadow"] is False
    assert reread["finish"] == "layer-lines"


def test_render_settings_route_post_rejects_invalid_new_fields(client, config_file):
    res = client.post("/api/render-settings", json={"finish": "matte"})
    assert res.status_code == 400
    assert "finish" in res.get_json()["error"].lower()

    res = client.post("/api/render-settings", json={"exposure": 10})
    assert res.status_code == 400

    res = client.post("/api/render-settings", json={"shadow": "yes"})
    assert res.status_code == 400

    # rejected writes did not stick
    assert client.get("/api/render-settings").get_json()["finish"] == "smooth"


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
    assert client.get("/api/render-settings").get_json()["color"] == "#0d0d0d"
