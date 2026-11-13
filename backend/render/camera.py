"""Camera Intent conversion: three.js (Y-up) preview -> Blender (Z-up) render camera.

The Step 4 preview runs in three.js (Y-up); Blender renders Z-up. The mapping
between the two worlds is a rigid rotation, so converting both the camera
position and the look-at target with ``three_to_blender`` makes the Blender
render show exactly the angle the user framed in the preview. Only the
*direction* (and FOV) are carried over — the Blender script auto-computes the
distance to frame the whole model (GLOSSARY.md: Camera Intent).
"""

import math


def three_to_blender(point) -> tuple[float, float, float]:
    """Map a three.js (Y-up) point to Blender (Z-up): (x, y, z) -> (x, -z, y)."""
    x, y, z = (float(c) for c in point)
    return (x, -z, y)


def compute_blender_camera(position, target) -> tuple[float, float]:
    """Convert a preview camera position + look-at target (three.js coords) to
    Blender azimuth/elevation in degrees, matching blender_studio.py's
    ``--azimuth``/``--elevation`` convention (direction from target to camera:
    azimuth in the XY plane from +X, elevation above the XY plane).

    Raises ValueError if position == target (no viewing direction).
    """
    px, py, pz = three_to_blender(position)
    tx, ty, tz = three_to_blender(target)
    dx, dy, dz = px - tx, py - ty, pz - tz
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length == 0:
        raise ValueError("camera position and target must differ")
    azimuth = math.degrees(math.atan2(dy, dx))
    elevation = math.degrees(math.asin(dz / length))
    return azimuth, elevation
