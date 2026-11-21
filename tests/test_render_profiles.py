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


# --- persistence seam: render profiles helpers ---

def test_get_render_profiles_defaults_to_empty(config_file):
    assert combine_data.get_render_profiles() == {}


def test_get_active_render_profile_defaults_to_none(config_file):
    # null active = "Current Settings" (the implicit default, not a stored profile)
    assert combine_data.get_active_render_profile() is None


def test_save_render_profile_roundtrip(config_file):
    settings = {"color": "#ff0000", "roughness": 0.8, "resolution": 512, "fov": 60}
    saved = combine_data.save_render_profile("My Profile", settings)
    assert saved == {"name": "My Profile", "settings": settings}

    profiles = combine_data.get_render_profiles()
    assert profiles == {"My Profile": settings}

    assert db.get_preference("render_profiles") == {"My Profile": settings}


def test_save_render_profile_overwrites_same_name(config_file):
    combine_data.save_render_profile("Studio", {"color": "#111111", "roughness": 0.2, "resolution": 512, "fov": 30})
    combine_data.save_render_profile("Studio", {"color": "#222222", "roughness": 0.9, "resolution": 2048, "fov": 50})
    profiles = combine_data.get_render_profiles()
    assert profiles == {"Studio": {"color": "#222222", "roughness": 0.9, "resolution": 2048, "fov": 50}}


def test_save_render_profile_preserves_extra_keys(config_file):
    # Ticket 02 will add fields (surface finish, lighting, shot mode...); the
    # profile snapshot must carry them without a schema migration.
    settings = {"color": "#1a1a1a", "roughness": 0.3, "resolution": 1024, "fov": 40,
                "surface_finish": "layer_lines", "layer_height": 0.2}
    combine_data.save_render_profile("Future", settings)
    assert combine_data.get_render_profiles()["Future"] == settings


@pytest.mark.parametrize("name", ["", "   ", None, "Current Settings", "current settings", "active"])
def test_save_render_profile_rejects_bad_names(config_file, name):
    with pytest.raises(ValueError):
        combine_data.save_render_profile(name, {"color": "#1a1a1a"})
    assert combine_data.get_render_profiles() == {}


@pytest.mark.parametrize("settings", [
    {"color": "red"},
    {"roughness": 1.5},
    {"resolution": 1000},
    {"fov": 90},
    "not-a-dict",
])
def test_save_render_profile_rejects_invalid_settings(config_file, settings):
    with pytest.raises(ValueError):
        combine_data.save_render_profile("P", settings)
    assert combine_data.get_render_profiles() == {}


# The full Render Settings surface is validated with the same per-field rules
# as save_render_settings: a profile must never snapshot values the flat
# settings would reject.
@pytest.mark.parametrize("settings", [
    {"finish": "matte"},
    {"layer_height_mm": 0.5},
    {"layer_height_mm": 0.01},
    {"layer_depth": 1.5},
    {"layer_depth": -0.1},
    {"key_energy": 2001},
    {"fill_energy": -1},
    {"rim_energy": "lots"},
    {"ambient": 2.1},
    {"shadow": "yes"},
    {"shadow_softness": 0.05},
    {"shadow_softness": 11},
    {"exposure": 0.05},
    {"exposure": 5},
    {"shot_mode": "burst"},
    {"rig": "not-a-list"},
    {"rig": [{"azimuth": 0}]},
    {"rig": [{"azimuth": 0, "elevation": 0, "roll": 5}]},
    {"rig": [{"azimuth": 400, "elevation": 0}]},
    {"rig": [{"azimuth": 0, "elevation": 91}]},
    {"rig": [{"azimuth": "north", "elevation": 0}]},
])
def test_save_render_profile_rejects_invalid_full_surface(config_file, settings):
    with pytest.raises(ValueError):
        combine_data.save_render_profile("P", settings)
    assert combine_data.get_render_profiles() == {}


def test_save_render_profile_accepts_full_surface(config_file):
    settings = {
        "color": "#3366cc", "roughness": 0.5, "resolution": 2048, "fov": 55,
        "finish": "layer-lines", "layer_height_mm": 0.3, "layer_depth": 0.7,
        "key_energy": 200, "fill_energy": 80, "rim_energy": 300, "ambient": 0.5,
        "shadow": False, "shadow_softness": 2.5, "exposure": 1.2,
        "shot_mode": "multi",
        "rig": [{"azimuth": -45, "elevation": 30}, {"azimuth": 180, "elevation": -89}],
    }
    saved = combine_data.save_render_profile("Full", settings)
    assert saved == {"name": "Full", "settings": settings}
    assert combine_data.get_render_profiles()["Full"] == settings


def test_save_render_profile_normalizes_rig_numbers(config_file):
    # validate_rig coerces numeric strings, same as the flat settings path
    combine_data.save_render_profile("Rig", {"rig": [{"azimuth": "45", "elevation": "10"}]})
    assert combine_data.get_render_profiles()["Rig"] == {"rig": [{"azimuth": 45.0, "elevation": 10.0}]}


def test_delete_render_profile(config_file):
    combine_data.save_render_profile("A", {"color": "#111111"})
    combine_data.save_render_profile("B", {"color": "#222222"})
    assert combine_data.delete_render_profile("A") is True
    assert combine_data.get_render_profiles() == {"B": {"color": "#222222"}}
    assert combine_data.delete_render_profile("A") is False


def test_active_render_profile_roundtrip(config_file):
    combine_data.save_render_profile("Studio", {"color": "#111111"})
    assert combine_data.set_active_render_profile("Studio") == "Studio"
    assert combine_data.get_active_render_profile() == "Studio"
    assert db.get_preference("active_render_profile") == "Studio"


def test_set_active_render_profile_rejects_unknown(config_file):
    with pytest.raises(ValueError):
        combine_data.set_active_render_profile("Nope")
    assert combine_data.get_active_render_profile() is None


def test_set_active_render_profile_none_means_current_settings(config_file):
    combine_data.save_render_profile("Studio", {"color": "#111111"})
    combine_data.set_active_render_profile("Studio")
    assert combine_data.set_active_render_profile(None) is None
    assert combine_data.get_active_render_profile() is None


def test_deleting_active_profile_resets_to_current_settings(config_file):
    combine_data.save_render_profile("Studio", {"color": "#111111"})
    combine_data.set_active_render_profile("Studio")
    combine_data.delete_render_profile("Studio")
    assert combine_data.get_active_render_profile() is None
    assert db.get_preference("active_render_profile") is None


# --- HTTP seam: /api/render-profiles ---

def test_route_get_empty_profiles(client, config_file):
    res = client.get("/api/render-profiles")
    assert res.status_code == 200
    assert res.get_json() == {"profiles": {}, "active": None}


def test_route_create_then_list(client, config_file):
    settings = {"color": "#3366cc", "roughness": 0.5, "resolution": 2048, "fov": 55}
    res = client.post("/api/render-profiles", json={"name": "Studio", "settings": settings})
    assert res.status_code == 201
    assert res.get_json() == {"name": "Studio", "settings": settings}

    listed = client.get("/api/render-profiles").get_json()
    assert listed["profiles"] == {"Studio": settings}
    assert listed["active"] is None


def test_route_create_rejects_duplicate_name(client, config_file):
    body = {"name": "Studio", "settings": {"color": "#3366cc"}}
    assert client.post("/api/render-profiles", json=body).status_code == 201
    res = client.post("/api/render-profiles", json=body)
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"].lower()


def test_route_create_rejects_invalid(client, config_file):
    res = client.post("/api/render-profiles", json={"name": "", "settings": {}})
    assert res.status_code == 400
    res = client.post("/api/render-profiles", json={"name": "X", "settings": {"color": "red"}})
    assert res.status_code == 400
    assert client.get("/api/render-profiles").get_json()["profiles"] == {}


def test_route_update_overwrites_by_name(client, config_file):
    client.post("/api/render-profiles", json={"name": "Studio", "settings": {"color": "#111111"}})
    res = client.post("/api/render-profiles/Studio", json={"settings": {"color": "#222222", "fov": 50}})
    assert res.status_code == 200
    assert client.get("/api/render-profiles").get_json()["profiles"]["Studio"] == {"color": "#222222", "fov": 50}

    # PUT works too
    res = client.put("/api/render-profiles/Studio", json={"settings": {"color": "#333333"}})
    assert res.status_code == 200
    assert client.get("/api/render-profiles").get_json()["profiles"]["Studio"] == {"color": "#333333"}


def test_route_update_missing_profile_returns_404(client, config_file):
    res = client.post("/api/render-profiles/Ghost", json={"settings": {"color": "#111111"}})
    assert res.status_code == 404


def test_route_delete(client, config_file):
    client.post("/api/render-profiles", json={"name": "Studio", "settings": {"color": "#111111"}})
    res = client.delete("/api/render-profiles/Studio")
    assert res.status_code == 200
    assert client.get("/api/render-profiles").get_json()["profiles"] == {}
    assert client.delete("/api/render-profiles/Studio").status_code == 404


def test_route_set_active(client, config_file):
    client.post("/api/render-profiles", json={"name": "Studio", "settings": {"color": "#111111"}})
    res = client.post("/api/render-profiles/active", json={"name": "Studio"})
    assert res.status_code == 200
    assert client.get("/api/render-profiles").get_json()["active"] == "Studio"

    # null name = back to "Current Settings"
    res = client.post("/api/render-profiles/active", json={"name": None})
    assert res.status_code == 200
    assert client.get("/api/render-profiles").get_json()["active"] is None


def test_route_set_active_unknown_profile_400(client, config_file):
    res = client.post("/api/render-profiles/active", json={"name": "Ghost"})
    assert res.status_code == 400


def test_route_delete_active_profile_resets_to_current_settings(client, config_file):
    client.post("/api/render-profiles", json={"name": "Studio", "settings": {"color": "#111111"}})
    client.post("/api/render-profiles/active", json={"name": "Studio"})
    client.delete("/api/render-profiles/Studio")
    assert client.get("/api/render-profiles").get_json()["active"] is None


def test_route_profiles_survive_restart(client, config_file):
    # Same on-disk config read by fresh calls simulates a server restart.
    client.post("/api/render-profiles", json={"name": "Studio", "settings": {"color": "#111111"}})
    client.post("/api/render-profiles/active", json={"name": "Studio"})
    fresh = app.test_client()
    listed = fresh.get("/api/render-profiles").get_json()
    assert listed["profiles"] == {"Studio": {"color": "#111111"}}
    assert listed["active"] == "Studio"
