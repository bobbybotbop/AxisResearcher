import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path

import pytest
from PIL import Image

from backend.render import get_blender_path, render_model

BLENDER_AVAILABLE = Path(get_blender_path()).exists()
pytestmark = pytest.mark.skipif(not BLENDER_AVAILABLE, reason="Blender not installed")

# 1x1x1 cube centered at origin, 12 triangles
CUBE_STL = """solid cube
  facet normal 0 0 -1
    outer loop
      vertex -0.5 -0.5 -0.5
      vertex 0.5 0.5 -0.5
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
      vertex 0.5 0.5 0.5
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


def test_render_produces_studio_shot(tmp_path):
    mesh = tmp_path / "cube.stl"
    mesh.write_text(CUBE_STL)
    output = tmp_path / "render.png"

    render_model(mesh, output, resolution=256, timeout=90)

    assert output.exists()
    image = Image.open(output).convert("RGB")
    assert image.size == (256, 256)
    pixels = image.load()
    # background blown to pure white in every corner
    for x, y in [(2, 2), (253, 2), (2, 253), (253, 253)]:
        r, g, b = pixels[x, y]
        assert r >= 245 and g >= 245 and b >= 245, f"corner ({x},{y}) = {(r, g, b)}"
    # glossy near-black model visible in the middle
    dark = sum(
        1
        for x in range(64, 192, 4)
        for y in range(64, 192, 4)
        if max(pixels[x, y]) < 100
    )
    assert dark > 20, "expected the near-black model in the center"


def _scaled_stl(stl, sx, sy, sz):
    """Scale every vertex of an ASCII STL — makes an asymmetric box from CUBE_STL."""
    out = []
    for line in stl.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] == "vertex":
            x, y, z = (float(parts[i]) for i in (1, 2, 3))
            line = f"      vertex {x * sx} {y * sy} {z * sz}"
        out.append(line)
    return "\n".join(out)


def _dark_pixel_bbox(image):
    """Bounding box of the dark (model) pixels: (width, height) in pixels."""
    pixels = image.load()
    xs, ys = [], []
    for x in range(0, image.size[0], 2):
        for y in range(0, image.size[1], 2):
            if max(pixels[x, y]) < 100:
                xs.append(x)
                ys.append(y)
    assert xs and ys, "expected a visible model silhouette"
    return max(xs) - min(xs), max(ys) - min(ys)


def test_render_matches_camera_intent_angle(tmp_path):
    """Camera Intent: the render's perspective follows the requested angle.

    A box wide in x, thin in y, tall in z looks wide from the front (azimuth
    90, camera on +Y sees the x-z face) and narrow from the side (azimuth 0,
    camera on +X sees the y-z face). If the angle were ignored, both
    silhouettes would have the same aspect ratio.
    """
    mesh = tmp_path / "box.stl"
    mesh.write_text(_scaled_stl(CUBE_STL, 2.0, 0.5, 1.0))
    front = tmp_path / "front.png"
    side = tmp_path / "side.png"

    render_model(mesh, front, resolution=256, azimuth=90, elevation=15, fov=40, timeout=90)
    render_model(mesh, side, resolution=256, azimuth=0, elevation=15, fov=40, timeout=90)

    front_w, front_h = _dark_pixel_bbox(Image.open(front).convert("RGB"))
    side_w, side_h = _dark_pixel_bbox(Image.open(side).convert("RGB"))
    assert front_w / front_h > 1.4, f"front view should be wide, got {front_w}x{front_h}"
    assert side_w / side_h < 0.8, f"side view should be narrow, got {side_w}x{side_h}"


def test_render_applies_model_color(tmp_path):
    mesh = tmp_path / "cube.stl"
    mesh.write_text(CUBE_STL)
    output = tmp_path / "render_red.png"

    render_model(mesh, output, color="#ff0000", resolution=256, timeout=90)

    assert output.exists()
    image = Image.open(output).convert("RGB")
    pixels = image.load()
    # a red model must survive the white-background compositor with its hue intact
    red = sum(
        1
        for x in range(64, 192, 4)
        for y in range(64, 192, 4)
        if pixels[x, y][0] > pixels[x, y][1] + 40 and pixels[x, y][0] > pixels[x, y][2] + 40
    )
    assert red > 20, "expected the red model in the center"
