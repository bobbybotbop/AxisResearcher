"""Studio Render (Step 4): render a 3D model to a product photo via headless Blender.

Public seam: render_model(). See .scratch/studio-render/spec.md.
"""

import os
import subprocess
from pathlib import Path

from backend.constants.render import (
    BLENDER_PATH_ENV_VAR,
    DEFAULT_BLENDER_PATH,
    DEFAULT_RENDER_AZIMUTH,
    DEFAULT_RENDER_COLOR,
    DEFAULT_RENDER_ELEVATION,
    DEFAULT_RENDER_FOV,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_ROUGHNESS,
    NATIVE_RENDER_EXTENSIONS,
    RENDER_TIMEOUT_SECONDS,
)

BLENDER_SCRIPT = Path(__file__).parent / "blender_studio.py"


class RenderError(Exception):
    """Friendly, user-presentable render failure."""


class UnsupportedFormatError(RenderError):
    """The uploaded model is not a natively renderable format."""


class BlenderNotFoundError(RenderError):
    """The Blender executable could not be found."""


def get_blender_path() -> str:
    """Blender exe path: BLENDER_PATH env var, else the documented default install."""
    return os.environ.get(BLENDER_PATH_ENV_VAR) or DEFAULT_BLENDER_PATH


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    hex_value = color.lstrip("#")
    if len(hex_value) != 6:
        raise RenderError(f"Invalid color '{color}': expected a hex value like #1a1a1a")
    try:
        return tuple(int(hex_value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        raise RenderError(f"Invalid color '{color}': expected a hex value like #1a1a1a")


def render_model(
    input_path,
    output_path,
    *,
    color: str = DEFAULT_RENDER_COLOR,
    roughness: float = DEFAULT_RENDER_ROUGHNESS,
    resolution: int = DEFAULT_RENDER_RESOLUTION,
    azimuth: float = DEFAULT_RENDER_AZIMUTH,
    elevation: float = DEFAULT_RENDER_ELEVATION,
    fov: float = DEFAULT_RENDER_FOV,
    blender_path: str | None = None,
    timeout: int = RENDER_TIMEOUT_SECONDS,
) -> Path:
    """Render a native-format mesh (.stl/.obj/.ply) to a studio product shot PNG.

    azimuth/elevation/fov are Blender-space camera angles (see
    backend.render.camera for the three.js -> Blender conversion). Distance is
    auto-computed by the Blender script to frame the whole model.

    Raises RenderError (or a subclass) with a friendly message on any failure.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    extension = input_path.suffix.lower()
    if extension not in NATIVE_RENDER_EXTENSIONS:
        raise UnsupportedFormatError(
            f"'{extension or input_path.name}' files are not supported for rendering yet. "
            f"Supported formats: {', '.join(NATIVE_RENDER_EXTENSIONS)}"
        )
    if not input_path.exists():
        raise RenderError(f"Model file not found: {input_path.name}")

    blender = blender_path or get_blender_path()
    if not Path(blender).exists():
        raise BlenderNotFoundError(
            "Blender was not found. Set the BLENDER_PATH environment variable "
            "to your blender.exe (e.g. C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe)."
        )

    red, green, blue = _hex_to_rgb(color)
    resolution = int(resolution)
    roughness = float(roughness)

    command = [
        blender,
        "--background",
        "--python", str(BLENDER_SCRIPT),
        "--",
        "--input", str(input_path.resolve()),
        "--output", str(output_path.resolve()),
        "--color", f"{red:.6f}", f"{green:.6f}", f"{blue:.6f}",
        "--roughness", f"{roughness:.4f}",
        "--resolution", str(resolution),
        "--azimuth", f"{float(azimuth):.4f}",
        "--elevation", f"{float(elevation):.4f}",
        "--fov", f"{float(fov):.4f}",
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RenderError(
            f"Rendering took too long (over {timeout}s) and was stopped. "
            "Try a lower resolution."
        )
    except OSError as e:
        raise RenderError(f"Could not start Blender: {e}")

    if completed.returncode != 0 or not output_path.exists():
        tail = (completed.stdout or "")[-500:] + (completed.stderr or "")[-500:]
        print(f"[render] Blender failed (exit {completed.returncode}): {tail}")
        raise RenderError(
            "Blender could not render this model. "
            "The file may be corrupt or not a valid 3D mesh."
        )

    return output_path
