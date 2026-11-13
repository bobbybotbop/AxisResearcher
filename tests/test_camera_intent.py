import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math

import pytest

from backend.render.camera import compute_blender_camera, three_to_blender


def test_three_to_blender_swaps_up_axis():
    # three.js is Y-up, Blender is Z-up: (x, y, z)_three -> (x, -z, y)_blender
    assert three_to_blender((1.0, 2.0, 3.0)) == (1.0, -3.0, 2.0)
    # three.js "up" becomes Blender "up"
    assert three_to_blender((0.0, 1.0, 0.0)) == (0.0, 0.0, 1.0)


def test_camera_looking_down_minus_z_in_three():
    # Preview camera 5 units along three.js +Z, looking at the origin:
    # in Blender that is 5 units along -Y -> azimuth -90, elevation 0
    azimuth, elevation = compute_blender_camera((0.0, 0.0, 5.0), (0.0, 0.0, 0.0))
    assert azimuth == pytest.approx(-90.0)
    assert elevation == pytest.approx(0.0, abs=1e-6)


def test_camera_directly_above_in_three():
    # Preview camera straight "up" in three.js (+Y) is straight up in Blender (+Z)
    azimuth, elevation = compute_blender_camera((0.0, 5.0, 0.0), (0.0, 0.0, 0.0))
    assert elevation == pytest.approx(90.0)


def test_camera_on_three_x_axis_stays_on_x_axis():
    azimuth, elevation = compute_blender_camera((5.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    assert azimuth == pytest.approx(0.0, abs=1e-6)
    assert elevation == pytest.approx(0.0, abs=1e-6)


def test_camera_angles_use_direction_only():
    # Same viewing direction from twice as far gives the same angles;
    # distance is auto-computed by the renderer (Camera Intent)
    near = compute_blender_camera((1.0, 1.0, -1.0), (0.0, 0.0, 0.0))
    far = compute_blender_camera((2.0, 2.0, -2.0), (0.0, 0.0, 0.0))
    assert near[0] == pytest.approx(far[0])
    assert near[1] == pytest.approx(far[1])


def test_camera_direction_accounts_for_look_at_target():
    # Camera beside the model but looking sideways at an off-center target
    # views along three.js -X -> Blender -X -> azimuth 180
    azimuth, elevation = compute_blender_camera((5.0, 0.0, 0.0), (10.0, 0.0, 0.0))
    assert azimuth == pytest.approx(180.0)
    assert elevation == pytest.approx(0.0, abs=1e-6)


def test_known_diagonal_angle():
    # three.js direction (1, 1, -1) normalized -> Blender (1, 1, 1) normalized:
    # azimuth 45, elevation asin(1/sqrt(3)) ~= 35.26
    azimuth, elevation = compute_blender_camera((1.0, 1.0, -1.0), (0.0, 0.0, 0.0))
    assert azimuth == pytest.approx(45.0)
    assert elevation == pytest.approx(math.degrees(math.asin(1 / math.sqrt(3))))
