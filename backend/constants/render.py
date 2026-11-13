# Studio Render (Step 4) constants. See .scratch/studio-render/spec.md and
# docs/adr/0001-studio-render-pipeline.md.

# Formats Blender 3.6 imports natively; others are normalized in a later ticket.
NATIVE_RENDER_EXTENSIONS: tuple[str, ...] = (".stl", ".obj", ".ply")

# Render Settings defaults (spec: near-black, slightly glossy, 1024x1024)
DEFAULT_RENDER_COLOR = "#1a1a1a"
DEFAULT_RENDER_ROUGHNESS = 0.3
DEFAULT_RENDER_RESOLUTION = 1024
RENDER_RESOLUTIONS: tuple[int, ...] = (512, 1024, 2048)

# Camera Intent defaults (spec: FOV slider 20-80 deg, default 40; the fixed
# azimuth/elevation used when the request carries no preview camera)
DEFAULT_RENDER_FOV = 40.0
RENDER_FOV_RANGE: tuple[float, float] = (20.0, 80.0)
DEFAULT_RENDER_AZIMUTH = 45.0
DEFAULT_RENDER_ELEVATION = 28.0

# Soft target ~30s; hard kill is hang protection only (ADR 0001)
RENDER_TIMEOUT_SECONDS = 90

# Blender 3.6.1 is the one external install; override with the BLENDER_PATH env var.
BLENDER_PATH_ENV_VAR = "BLENDER_PATH"
DEFAULT_BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"

# Output naming mirrors the existing generated-images convention
RENDER_OUTPUT_PREFIX = "generated_render_"
