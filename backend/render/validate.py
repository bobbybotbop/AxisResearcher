"""Shared validation for Studio Render settings (roughness / resolution / fov).

Single home for the range checks and friendly messages used by both the
/api/render request path (app.py) and the persisted-settings path
(backend/copyScripts/combine_data.py), so the two cannot drift apart.
"""

from backend.constants.render import (
    RENDER_FOV_MAX,
    RENDER_FOV_MIN,
    RENDER_RESOLUTIONS,
)


def validate_roughness(value) -> float:
    """Coerce to float and enforce the Principled roughness range 0..1."""
    try:
        roughness = float(value)
    except (TypeError, ValueError):
        raise ValueError("roughness must be a number between 0 and 1")
    if not 0.0 <= roughness <= 1.0:
        raise ValueError("roughness must be between 0 and 1")
    return roughness


def validate_resolution(value) -> int:
    """Coerce to int and enforce membership in RENDER_RESOLUTIONS."""
    try:
        resolution = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"resolution must be one of {list(RENDER_RESOLUTIONS)}")
    if resolution not in RENDER_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {list(RENDER_RESOLUTIONS)}")
    return resolution


def validate_fov(value) -> float:
    """Coerce to float and enforce the FOV slider range (degrees)."""
    try:
        fov = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"fov must be a number between {RENDER_FOV_MIN} and {RENDER_FOV_MAX}")
    if not RENDER_FOV_MIN <= fov <= RENDER_FOV_MAX:
        raise ValueError(f"fov must be between {RENDER_FOV_MIN} and {RENDER_FOV_MAX}")
    return fov
