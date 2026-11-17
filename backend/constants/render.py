# Studio Render (Step 4) constants. See .scratch/studio-render/spec.md and
# docs/adr/0001-studio-render-pipeline.md.

# Formats Blender 3.6 imports natively; others are normalized to STL first
# (backend/render/normalize.py) so preview and render share one Render Mesh.
NATIVE_RENDER_EXTENSIONS: tuple[str, ...] = (".stl", ".obj", ".ply")

# Uploads normalized to STL before Blender sees them: .step/.stp via the gmsh
# pip wheel, .3mf via trimesh (ADR 0001). .amf is unsupported everywhere.
CONVERTIBLE_RENDER_EXTENSIONS: tuple[str, ...] = (".3mf", ".step", ".stp")

SUPPORTED_RENDER_EXTENSIONS: tuple[str, ...] = NATIVE_RENDER_EXTENSIONS + CONVERTIBLE_RENDER_EXTENSIONS

# Render Settings defaults (spec: near-black, slightly glossy, 1024x1024)
DEFAULT_RENDER_COLOR = "#1a1a1a"
DEFAULT_RENDER_ROUGHNESS = 0.3
DEFAULT_RENDER_RESOLUTION = 1024
RENDER_RESOLUTIONS: tuple[int, ...] = (512, 1024, 2048)

# Camera Intent / persisted FOV (spec: FOV slider 20-80 deg, default 40; the
# fixed azimuth/elevation used when the request carries no preview camera)
DEFAULT_RENDER_FOV = 40.0
RENDER_FOV_MIN = 20.0
RENDER_FOV_MAX = 80.0
RENDER_FOV_RANGE: tuple[float, float] = (RENDER_FOV_MIN, RENDER_FOV_MAX)
DEFAULT_RENDER_AZIMUTH = 45.0
DEFAULT_RENDER_ELEVATION = 28.0

# Lighting rig (spec: 3-point area lights; defaults reproduce the original
# hardcoded energies so a default render is pixel-identical to before)
DEFAULT_RENDER_KEY_ENERGY = 150.0
DEFAULT_RENDER_FILL_ENERGY = 60.0
DEFAULT_RENDER_RIM_ENERGY = 250.0
RENDER_ENERGY_MAX = 2000.0  # sanity ceiling for persisted/posted intensities
# World (ambient) background strength
DEFAULT_RENDER_AMBIENT = 0.35
RENDER_AMBIENT_MAX = 2.0
# Shadows: only the key light casts one; softness is the key light's disk size
DEFAULT_RENDER_SHADOW = True
DEFAULT_RENDER_SHADOW_SOFTNESS = 1.5
RENDER_SHADOW_SOFTNESS_MIN = 0.1
RENDER_SHADOW_SOFTNESS_MAX = 10.0
# Exposure: global multiplier on all light energies + world strength
DEFAULT_RENDER_EXPOSURE = 1.0
RENDER_EXPOSURE_MIN = 0.1
RENDER_EXPOSURE_MAX = 4.0

# Surface Finish (GLOSSARY): Smooth Plastic or Layer Lines (FDM bump)
RENDER_FINISHES: tuple[str, ...] = ("smooth", "layer-lines")
DEFAULT_RENDER_FINISH = "smooth"
DEFAULT_RENDER_LAYER_HEIGHT_MM = 0.2  # real FDM layer height
RENDER_LAYER_HEIGHT_MM_MIN = 0.08
RENDER_LAYER_HEIGHT_MM_MAX = 0.4
DEFAULT_RENDER_LAYER_DEPTH = 0.4  # bump strength
RENDER_LAYER_DEPTH_MIN = 0.0
RENDER_LAYER_DEPTH_MAX = 1.0

# Soft target ~30s; hard kill is hang protection only (ADR 0001)
RENDER_TIMEOUT_SECONDS = 90

# Blender 3.6.1 is the one external install; override with the BLENDER_PATH env var.
BLENDER_PATH_ENV_VAR = "BLENDER_PATH"
DEFAULT_BLENDER_PATH = r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"

# Output naming mirrors the existing generated-images convention
RENDER_OUTPUT_PREFIX = "generated_render_"
