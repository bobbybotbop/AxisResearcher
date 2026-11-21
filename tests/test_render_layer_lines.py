"""Structural tests for the Layer Lines surface finish in blender_studio.py.

Blender can't run inside pytest, so these tests assert on the render script's
structure: the CLI args it accepts and the node graph it builds. Actual pixel
verification is manual (see the ticket's timed A/B render).

Surface Finish vocabulary per GLOSSARY.md: Smooth Plastic (plain Principled
BSDF, today's behavior) or Layer Lines (procedural FDM layer-line bump:
Wave Texture Bands/Z -> Bump -> Principled Normal).
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


# --- CLI seam ---

def test_finish_arg_offers_smooth_and_layer_lines():
    args = _args_block()
    assert "--finish" in args
    # both finishes are valid choices, smooth stays the default
    assert "smooth" in args and "layer-lines" in args
    assert re.search(r'--finish.*?default\s*=\s*["\']smooth["\']', args, re.S)


def test_layer_height_mm_arg_is_float_with_fdm_default():
    args = _args_block()
    match = re.search(
        r'--layer-height-mm.*?type\s*=\s*float.*?default\s*=\s*([\d.]+)', args, re.S)
    assert match, "--layer-height-mm must be a float arg with a default"
    # GLOSSARY: real FDM layer heights 0.08-0.4mm, default 0.2mm
    assert float(match.group(1)) == pytest.approx(0.2)


def test_layer_depth_arg_is_float():
    args = _args_block()
    assert re.search(r'--layer-depth.*?type\s*=\s*float', args, re.S)


# --- node-graph seam ---

def test_layer_lines_builds_wave_bump_chain_into_principled_normal():
    """Wave Texture (Bands, Z) -> Bump -> Principled Normal, per the research."""
    assert "ShaderNodeTexWave" in SOURCE
    assert "ShaderNodeBump" in SOURCE
    assert re.search(r"wave_type\s*=\s*['\"]BANDS['\"]", SOURCE)
    assert re.search(r"bands_direction\s*=\s*['\"]Z['\"]", SOURCE)
    # Bump Normal feeds the Principled BSDF Normal input
    assert re.search(r'links\.new\(bump\.outputs\["Normal"\],\s*bsdf\.inputs\["Normal"\]\)', SOURCE)


def test_wave_scale_derives_from_layer_height_mm():
    """Layer height in real FDM mm converts to wave bands across the normalized
    2.0-unit model: scale = assumed real model height (mm) / layer height (mm),
    so 0.2mm on a 60mm part gives ~300 bands (research's starting value)."""
    match = re.search(r"ASSUMED_MODEL_HEIGHT_MM\s*=\s*([\d.]+)", SOURCE)
    assert match, "script must state the real-world height the mm value scales against"
    assert float(match.group(1)) == pytest.approx(60.0)
    assert re.search(r"ASSUMED_MODEL_HEIGHT_MM\s*/\s*layer_height_mm", SOURCE)


def test_smooth_finish_adds_no_bump_nodes():
    """Smooth must behave exactly as today: the wave/bump chain is conditional
    on the layer-lines finish, not unconditional."""
    apply = re.search(r"def apply_material\(.*?\n(?=\ndef )", SOURCE, re.S)
    assert apply, "apply_material() not found"
    body = apply.group(0)
    assert re.search(r"if\s+finish\s*==\s*['\"]layer-lines['\"]", body)


def test_bump_distance_is_large_enough_to_show_on_vertical_walls():
    """Regression: layer lines were invisible on vertical walls (only the roof,
    lit face-on, showed texture) because the Bump Distance (groove depth in
    scene units) was derived as 0.5 x layer spacing = 0.0033 units — too small
    to register a shading change at a glancing angle. A render sweep showed
    walls need Distance >= ~0.01 and read clearly at 0.02 (at the default
    0.2mm layer height). Assert the default-settings Distance meets the 0.01
    floor. Distance must also scale with layer_depth so the user knob controls
    visible depth."""
    apply = re.search(r"def apply_material\(.*?\n(?=\ndef )", SOURCE, re.S)
    assert apply, "apply_material() not found"
    body = apply.group(0)
    # Distance must reference layer_depth (the user knob), not be a fixed
    # fraction of layer spacing alone.
    dist_line = re.search(r'bump\.inputs\["Distance"\]\.default_value\s*=\s*(.+)', body)
    assert dist_line, "Bump Distance assignment not found"
    expr = dist_line.group(1)
    assert "layer_depth" in expr, (
        "Bump Distance must scale with layer_depth so the line-depth knob "
        "controls visible groove depth (fixed 0.5xspacing was wall-invisible)")
    # Evaluate the default: layer_depth=0.4, layer_height_mm=0.2, and the
    # script's constants. The result must clear the 0.01 wall-visibility floor.
    assumed = float(re.search(r"ASSUMED_MODEL_HEIGHT_MM\s*=\s*([\d.]+)", SOURCE).group(1))
    std = float(re.search(r"STANDARD_SIZE\s*=\s*([\d.]+)", SOURCE).group(1))
    env = {"layer_depth": 0.4, "layer_height_mm": 0.2,
           "ASSUMED_MODEL_HEIGHT_MM": assumed, "STANDARD_SIZE": std}
    value = eval(expr, {"__builtins__": {}}, env)  # noqa: S307 - arithmetic expr only
    assert value >= 0.01, (
        f"default Bump Distance {value:.4f} is below the 0.01 wall-visibility "
        "floor; walls will render smooth")
