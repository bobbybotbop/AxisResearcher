"""render_model() must forward the expanded Render Settings (lighting, shadow,
exposure, finish) to blender_studio.py as CLI flags. Blender is stubbed out;
the test captures the command line."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import subprocess

import pytest

from backend.render import render_model


@pytest.fixture()
def captured(tmp_path, monkeypatch):
    """Stub Blender: capture the argv render_model() builds and touch the output."""
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        output = command[command.index("--output") + 1]
        with open(output, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        class Done:
            returncode = 0
            stdout = ""
            stderr = ""
        return Done()

    monkeypatch.setattr(subprocess, "run", fake_run)
    mesh = tmp_path / "model.stl"
    mesh.write_text("solid x\nendsolid x\n")
    calls["mesh"] = mesh
    calls["out"] = tmp_path / "out.png"
    calls["blender"] = str(tmp_path / "blender.exe")
    open(calls["blender"], "w").close()  # must exist for the path check
    return calls


def _flag_value(command, flag):
    return command[command.index(flag) + 1]


def test_new_settings_default_to_spec_values(captured):
    """With no overrides the flags carry the spec defaults (today's render)."""
    render_model(captured["mesh"], captured["out"], blender_path=captured["blender"])
    command = captured["command"]
    assert _flag_value(command, "--key-energy") == "150.0000"
    assert _flag_value(command, "--fill-energy") == "60.0000"
    assert _flag_value(command, "--rim-energy") == "250.0000"
    assert _flag_value(command, "--ambient") == "0.3500"
    assert _flag_value(command, "--shadow-softness") == "1.5000"
    assert _flag_value(command, "--exposure") == "1.0000"
    assert _flag_value(command, "--finish") == "smooth"
    assert _flag_value(command, "--layer-height-mm") == "0.2000"
    assert _flag_value(command, "--layer-depth") == "0.4000"
    assert "--shadow" in command
    assert "--no-shadow" not in command


def test_new_settings_are_forwarded(captured):
    render_model(
        captured["mesh"], captured["out"],
        blender_path=captured["blender"],
        key_energy=300, fill_energy=20, rim_energy=500,
        ambient=0.8, shadow=False, shadow_softness=3.0, exposure=1.5,
        finish="layer-lines", layer_height_mm=0.12, layer_depth=0.7,
    )
    command = captured["command"]
    assert _flag_value(command, "--key-energy") == "300.0000"
    assert _flag_value(command, "--fill-energy") == "20.0000"
    assert _flag_value(command, "--rim-energy") == "500.0000"
    assert _flag_value(command, "--ambient") == "0.8000"
    assert _flag_value(command, "--shadow-softness") == "3.0000"
    assert _flag_value(command, "--exposure") == "1.5000"
    assert _flag_value(command, "--finish") == "layer-lines"
    assert _flag_value(command, "--layer-height-mm") == "0.1200"
    assert _flag_value(command, "--layer-depth") == "0.7000"
    assert "--no-shadow" in command
    assert "--shadow" not in command
