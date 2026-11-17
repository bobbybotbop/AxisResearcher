"""Regression test: rendering from below the model must not show a flat 2D plane.

When the camera is below the model (negative elevation), the ground plane at
z=0 blocks the view — the render shows a flat white surface instead of the
model's underside. The fix: flip the ground plane to the top of the model
when the camera is below it.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

import pytest
from PIL import Image

from backend.render import get_blender_path, render_model

BLENDER_AVAILABLE = Path(get_blender_path()).exists()
pytestmark = pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Blender not installed")

# 1x1x1 cube centered at origin, 12 triangles (same as test_render_studio.py)
CUBE_STL = """solid cube
  facet normal 0 0 -1
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex 0.5 -0.5 -0.5
      vertex 0.5 -0.5 -0.5
    endloop
  endfacet
  facet normal 0 0 -1
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex -0.5 0.5 -0.5
      vertex 0.5 0.5 -0.5
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex -0.5 -0.5 0.5
      vertex 0.5 -0.5 0.5
      vertex 0.5 0.5 0.5
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex -0.5 -0.5 0.5
      vertex 0.5 0.5 0.5
      vertex -0.5 0.5 0.5
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex 0.5 -0.5 -0.5
      vertex 0.5 -0.5 0.5
    endloop
  endfacet
  facet normal 0 -1 0
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex 0.5 -0.5 0.5
      vertex -0.5 -0.5 0.5
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex -0.5 0.5 -0.5
      vertex 0.5 0.5 0.5
      vertex 0.5 0.5 -0.5
    endloop
  endfacet
  facet normal 0 1 0
    outer loop
      vertex -0.5 0.5 -0.5
      vertex -0.5 0.5 0.5
      vertex 0.5 0.5 0.5
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex -0.5 -0.5 0.5
      vertex -0.5 0.5 0.5
    endloop
  endfacet
  facet normal -1 0 0
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex -0.5 0.5 0.5
      vertex -0.5 0.5 -0.5
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 0.5 -0.5 -0.5
      vertex 0.5 -0.5 0.5
      vertex 0.5 -0.5 0.5
    endloop
  endfacet
  facet normal 1 0 0
    outer loop
      vertex 0.5 -0.5 -0.5
      vertex 0.5 0.5 -0.5
      vertex 0.5 0.5 0.5
    endloop
  endfacet
endsolid cube
"""


def _dark_pixel_count(image: Image.Image) -> int:
    """Count pixels that are clearly the dark model, not the white background."""
    pixels = image.load()
    return sum(
        1
        for x in range(0, image.size[0], 2)
        for y in range(0, image.size[1], 2)
        if max(pixels[x, y]) < 100
    )


def _shading_variance(image: Image.Image) -> float:
    """Measure the variance of dark-pixel brightness — a proxy for 3D shading.

    A flat 2D silhouette (the bug) has nearly uniform dark pixels: low variance.
    A properly shaded 3D render has a gradient of dark-to-mid tones: high variance.
    """
    pixels = image.load()
    values = []
    for x in range(0, image.size[0], 2):
        for y in range(0, image.size[1], 2):
            r, g, b = pixels[x, y]
            if max(r, g, b) < 200:  # model pixels (not white background)
                values.append((r + g + b) / 3)
    if len(values) < 10:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def test_render_from_below_shows_model_not_flat_plane(tmp_path):
    """Camera below the model (negative elevation) must still show the model.

    With the ground plane at z=0 (the model's base), a camera at elevation=-30
    sees the underside of the ground plane — a flat white surface with no model
    visible. The fix flips the ground plane to the model's top when the camera
    is below, so the model's underside is visible with a shadow cast upward.
    """
    mesh = tmp_path / "cube.stl"
    mesh.write_text(CUBE_STL)
    output = tmp_path / "below.png"

    render_model(mesh, output, resolution=256, azimuth=45, elevation=-30, fov=40, timeout=90)

    assert output.exists()
    image = Image.open(output).convert("RGB")
    dark = _dark_pixel_count(image)
    variance = _shading_variance(image)
    # If the bug is present, the ground plane blocks the view and the model
    # renders as a flat silhouette with almost no shading variance.
    # Before the fix, the ground plane blocks the view: the model renders as a
    # small flat silhouette (~900 dark pixels at 256px). After the fix, the
    # full underside is visible with 3D shading (~7000 dark pixels at 256px).
    assert dark > 3000, (
        f"Expected the model's underside to fill much of the frame from below "
        f"(elevation=-30), but only found {dark} dark pixels — the ground "
        f"plane is likely blocking the view"
    )
    assert variance > 100, (
        f"Expected 3D shading from below (elevation=-30), "
        f"but shading variance is only {variance:.1f} — the model appears "
        f"as a flat 2D silhouette"
    )
