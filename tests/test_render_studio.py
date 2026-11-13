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
