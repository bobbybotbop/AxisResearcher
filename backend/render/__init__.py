"""Studio Render (Step 4): render a 3D model to a product photo via headless Blender.

Public seam: render_model(). See .scratch/studio-render/spec.md.
"""

import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

from backend.constants.render import (
    BLENDER_PATH_ENV_VAR,
    DEFAULT_BLENDER_PATH,
    DEFAULT_RENDER_AMBIENT,
    DEFAULT_RENDER_AZIMUTH,
    DEFAULT_RENDER_COLOR,
    DEFAULT_RENDER_ELEVATION,
    DEFAULT_RENDER_EXPOSURE,
    DEFAULT_RENDER_FILL_ENERGY,
    DEFAULT_RENDER_FINISH,
    DEFAULT_RENDER_FOV,
    DEFAULT_RENDER_KEY_ENERGY,
    DEFAULT_RENDER_LAYER_DEPTH,
    DEFAULT_RENDER_LAYER_HEIGHT_MM,
    DEFAULT_RENDER_RESOLUTION,
    DEFAULT_RENDER_RIM_ENERGY,
    DEFAULT_RENDER_ROUGHNESS,
    DEFAULT_RENDER_SHADOW,
    DEFAULT_RENDER_SHADOW_SOFTNESS,
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


# Cycles progress checkpoints, e.g.:
#   Fra:1 ... | Scene, ViewLayer | Sample 34/48
#   Fra:1 ... | Remaining:00:08.00 | ... | Scene, ViewLayer | Sample 1/48
_SAMPLE_RE = re.compile(r"\bSample\s+(\d+)/(\d+)")
_REMAINING_RE = re.compile(r"\bRemaining:(\d+):(\d+(?:\.\d+)?)")


def _parse_remaining_seconds(match: re.Match) -> float:
    minutes, seconds = int(match.group(1)), float(match.group(2))
    return minutes * 60 + seconds


def _prepare_render(input_path, output_path, color, roughness, resolution,
                    azimuth, elevation, fov, finish, layer_height_mm, layer_depth,
                    key_energy, fill_energy, rim_energy, ambient, shadow,
                    shadow_softness, exposure, blender_path):
    """Validate inputs and build the Blender command line."""
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
    command = [
        blender,
        "--background",
        "--python", str(BLENDER_SCRIPT),
        "--",
        "--input", str(input_path.resolve()),
        "--output", str(output_path.resolve()),
        "--color", f"{red:.6f}", f"{green:.6f}", f"{blue:.6f}",
        "--roughness", f"{float(roughness):.4f}",
        "--resolution", str(int(resolution)),
        "--azimuth", f"{float(azimuth):.4f}",
        "--elevation", f"{float(elevation):.4f}",
        "--fov", f"{float(fov):.4f}",
        "--finish", str(finish),
        "--layer-height-mm", f"{float(layer_height_mm):.4f}",
        "--layer-depth", f"{float(layer_depth):.4f}",
        "--key-energy", f"{float(key_energy):.4f}",
        "--fill-energy", f"{float(fill_energy):.4f}",
        "--rim-energy", f"{float(rim_energy):.4f}",
        "--ambient", f"{float(ambient):.4f}",
        "--shadow" if shadow else "--no-shadow",
        "--shadow-softness", f"{float(shadow_softness):.4f}",
        "--exposure", f"{float(exposure):.4f}",
    ]
    return command, output_path


def iter_render_progress(
    input_path,
    output_path,
    *,
    color: str = DEFAULT_RENDER_COLOR,
    roughness: float = DEFAULT_RENDER_ROUGHNESS,
    resolution: int = DEFAULT_RENDER_RESOLUTION,
    azimuth: float = DEFAULT_RENDER_AZIMUTH,
    elevation: float = DEFAULT_RENDER_ELEVATION,
    fov: float = DEFAULT_RENDER_FOV,
    finish: str = DEFAULT_RENDER_FINISH,
    layer_height_mm: float = DEFAULT_RENDER_LAYER_HEIGHT_MM,
    layer_depth: float = DEFAULT_RENDER_LAYER_DEPTH,
    key_energy: float = DEFAULT_RENDER_KEY_ENERGY,
    fill_energy: float = DEFAULT_RENDER_FILL_ENERGY,
    rim_energy: float = DEFAULT_RENDER_RIM_ENERGY,
    ambient: float = DEFAULT_RENDER_AMBIENT,
    shadow: bool = DEFAULT_RENDER_SHADOW,
    shadow_softness: float = DEFAULT_RENDER_SHADOW_SOFTNESS,
    exposure: float = DEFAULT_RENDER_EXPOSURE,
    blender_path: str | None = None,
    timeout: int = RENDER_TIMEOUT_SECONDS,
):
    """Drive Blender, yielding (current, total, remaining_seconds) per checkpoint.

    A generator: it runs Blender with Popen and yields each Cycles 'Sample N/M'
    checkpoint as the stdout line arrives, so a caller can stream live progress.
    remaining_seconds is None when the line carries no 'Remaining:MM:SS' ETA.
    Returns the output Path via StopIteration.value once the PNG exists.

    The lighting (key/fill/rim energy, ambient), shadow, exposure, and Surface
    Finish kwargs map to the Render Settings; their defaults reproduce the
    original render.

    Raises RenderError (or a subclass) with a friendly message on any failure.
    """
    command, output_path = _prepare_render(
        input_path, output_path, color, roughness, resolution,
        azimuth, elevation, fov, finish, layer_height_mm, layer_depth,
        key_energy, fill_energy, rim_energy, ambient, shadow,
        shadow_softness, exposure, blender_path,
    )

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as e:
        raise RenderError(f"Could not start Blender: {e}")

    stdout_lines = []
    timed_out = False
    deadline = time.monotonic() + timeout

    # Read stdout on a helper thread that pushes lines onto a queue, so the
    # deadline below is enforced with queue.get(timeout=...) instead of only
    # when a line arrives: a Blender that hangs while printing nothing would
    # otherwise block the read forever and the hard kill would never fire.
    lines: queue.Queue = queue.Queue()

    def _pump_stdout():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)  # EOF sentinel

    reader = threading.Thread(target=_pump_stdout, daemon=True)
    reader.start()

    try:
        while True:
            try:
                line = lines.get(timeout=max(deadline - time.monotonic(), 0))
            except queue.Empty:
                raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)
            if line is None:  # Blender closed stdout: it is exiting
                break
            stdout_lines.append(line)
            sample = _SAMPLE_RE.search(line)
            if sample:
                remaining_match = _REMAINING_RE.search(line)
                remaining = _parse_remaining_seconds(remaining_match) if remaining_match else None
                yield (int(sample.group(1)), int(sample.group(2)), remaining)
        process.wait(timeout=max(deadline - time.monotonic(), 0))
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        process.wait()

    if timed_out:
        raise RenderError(
            f"Rendering took too long (over {timeout}s) and was stopped. "
            "Try a lower resolution."
        )

    if process.returncode != 0 or not output_path.exists():
        tail = "".join(stdout_lines)[-1000:]
        print(f"[render] Blender failed (exit {process.returncode}): {tail}")
        raise RenderError(
            "Blender could not render this model. "
            "The file may be corrupt or not a valid 3D mesh."
        )

    return output_path


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
    finish: str = DEFAULT_RENDER_FINISH,
    layer_height_mm: float = DEFAULT_RENDER_LAYER_HEIGHT_MM,
    layer_depth: float = DEFAULT_RENDER_LAYER_DEPTH,
    key_energy: float = DEFAULT_RENDER_KEY_ENERGY,
    fill_energy: float = DEFAULT_RENDER_FILL_ENERGY,
    rim_energy: float = DEFAULT_RENDER_RIM_ENERGY,
    ambient: float = DEFAULT_RENDER_AMBIENT,
    shadow: bool = DEFAULT_RENDER_SHADOW,
    shadow_softness: float = DEFAULT_RENDER_SHADOW_SOFTNESS,
    exposure: float = DEFAULT_RENDER_EXPOSURE,
    blender_path: str | None = None,
    timeout: int = RENDER_TIMEOUT_SECONDS,
    on_progress=None,
) -> Path:
    """Render a native-format mesh (.stl/.obj/.ply) to a studio product shot PNG.

    azimuth/elevation/fov are Blender-space camera angles (see
    backend.render.camera for the three.js -> Blender conversion). Distance is
    auto-computed by the Blender script to frame the whole model. The lighting
    (key/fill/rim energy, ambient), shadow, exposure, and Surface Finish kwargs
    map to the Render Settings; their defaults reproduce the original render.

    on_progress, when given, is called as on_progress(current, total,
    remaining_seconds) for each Cycles 'Sample N/M' checkpoint Blender prints;
    remaining_seconds is None when the line carries no 'Remaining:MM:SS' ETA.

    Raises RenderError (or a subclass) with a friendly message on any failure.
    """
    events = iter_render_progress(
        input_path, output_path,
        color=color, roughness=roughness, resolution=resolution,
        azimuth=azimuth, elevation=elevation, fov=fov,
        finish=finish, layer_height_mm=layer_height_mm, layer_depth=layer_depth,
        key_energy=key_energy, fill_energy=fill_energy, rim_energy=rim_energy,
        ambient=ambient, shadow=shadow, shadow_softness=shadow_softness,
        exposure=exposure,
        blender_path=blender_path, timeout=timeout,
    )
    try:
        while True:
            current, total, remaining = next(events)
            if on_progress is not None:
                on_progress(current, total, remaining)
    except StopIteration as done:
        return done.value
