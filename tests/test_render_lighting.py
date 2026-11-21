"""Structural tests for the expanded lighting/shadow/exposure settings in
blender_studio.py.

Blender can't run inside pytest, so these tests assert on the render script's
structure: the CLI args it accepts and how the values reach the light rig and
world. Defaults must reproduce the original hardcoded render exactly
(key 150 / fill 60 / rim 250, world strength 0.35, key-only shadow, key size
1.5, exposure 1.0 = no scaling).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "backend" / "render" / "blender_studio.py"
SOURCE = SCRIPT.read_text(encoding="utf-8")


def _args_block():
    match = re.search(r"def parse_args\(\):.*?return parser\.parse_args", SOURCE, re.S)
    assert match, "parse_args() not found in blender_studio.py"
    return match.group(0)


# --- CLI seam: args exist with defaults that reproduce today's render ---

@pytest.mark.parametrize("flag,default", [
    ("--key-energy", 150.0),
    ("--fill-energy", 60.0),
    ("--rim-energy", 250.0),
    ("--ambient", 0.35),
    ("--shadow-softness", 1.5),
    ("--exposure", 1.0),
])
def test_lighting_args_are_floats_with_spec_defaults(flag, default):
    args = _args_block()
    match = re.search(
        re.escape(flag) + r".*?type\s*=\s*float.*?default\s*=\s*([\d.]+)", args, re.S)
    assert match, f"{flag} must be a float arg with a default"
    assert float(match.group(1)) == pytest.approx(default)


def test_shadow_arg_is_on_off_and_defaults_on():
    args = _args_block()
    assert "--shadow" in args
    # an on/off flag pair (or BooleanOptionalAction); default must be on
    assert re.search(r"--shadow", args)
    assert re.search(r"default\s*=\s*True", args) or "BooleanOptionalAction" in args


# --- wiring seam: the values reach the rig, the world, and exposure scales all ---

def test_rig_uses_arg_energies_not_hardcoded():
    """Key/fill/rim energies come from the parsed args (scaled by exposure),
    not the original hardcoded 150/60/250 literals."""
    main = re.search(r"def main\(\):.*", SOURCE, re.S)
    assert main, "main() not found"
    body = main.group(0)
    for name in ("Key", "Fill", "Rim"):
        assert re.search(
            rf'add_area_light\("{name}".*?energy\s*=\s*\w+', body, re.S
        ), f"{name} light energy must come from a variable, not a literal"
    # no leftover hardcoded energy literals in the rig setup
    assert not re.search(r'add_area_light\("Key".*?energy\s*=\s*150\b', body, re.S)
    assert not re.search(r'add_area_light\("Fill".*?energy\s*=\s*60\b', body, re.S)
    assert not re.search(r'add_area_light\("Rim".*?energy\s*=\s*250\b', body, re.S)


def test_exposure_multiplies_energies_and_world():
    """Exposure is a global multiplier: every light energy and the world
    strength are scaled by it."""
    main = re.search(r"def main\(\):.*", SOURCE, re.S).group(0)
    assert re.search(r"args\.exposure\s*\*", main) or re.search(r"\*\s*args\.exposure", main), \
        "exposure must multiply the light energies"
    world = re.search(r'inputs\[1\]\.default_value\s*=\s*(.+)', main)
    assert world and "exposure" in world.group(1), \
        "world strength must be scaled by exposure"


def test_world_strength_comes_from_ambient_arg():
    main = re.search(r"def main\(\):.*", SOURCE, re.S).group(0)
    assert re.search(r"inputs\[1\]\.default_value\s*=\s*.*args\.ambient", main), \
        "world Background strength must come from --ambient"


def test_shadow_toggle_and_softness_reach_key_light():
    """Shadow on/off drives the key light's use_shadow; softness is its size."""
    main = re.search(r"def main\(\):.*", SOURCE, re.S).group(0)
    key = re.search(r'add_area_light\("Key".*', main)
    assert key, "Key light setup not found"
    assert "shadow" in key.group(0), "Key light must receive the shadow toggle"
    assert re.search(r"size\s*=\s*\w*softness", key.group(0)) or \
           re.search(r"size\s*=\s*args\.shadow_softness", key.group(0)), \
        "Key light size must come from --shadow-softness"
