// Studio Render (Step 4) constants, mirroring backend/constants/render.py.

// Formats Blender imports natively — everything else the backend normalizes to
// an STL Render Mesh (.step/.stp via gmsh, .3mf via trimesh) before rendering.
export const NATIVE_RENDER_EXTENSIONS = [".obj", ".stl", ".ply"];
// Renderable candidates, mirrors backend PREFERRED_3D_EXTENSIONS order
export const RENDER_CANDIDATE_EXTENSIONS = [".3mf", ".step", ".stp", ".obj", ".stl", ".ply"];
// Human-readable supported-format list for Step 4 empty-state messages
export const RENDERABLE_FORMATS_HINT = RENDER_CANDIDATE_EXTENSIONS.join("/");

// Lowercase file extension including the dot
export const modelExtensionOf = (name: string) => name.slice(name.lastIndexOf(".")).toLowerCase();

// Render Settings defaults (persisted via /api/render-settings; spec defaults as
// fallback). The UI exposes "Glossiness"; the persisted/wire value is Principled
// roughness (glossiness = 1 − roughness).
export const RENDER_SETTINGS_DEFAULTS = { color: "#1a1a1a", roughness: 0.3, resolution: 1024, fov: 40 };
export const RENDER_RESOLUTION_OPTIONS = [512, 1024, 2048];
export const RENDER_FOV_MIN = 20;
export const RENDER_FOV_MAX = 80;

// Slider/color inputs fire many events while dragging; persist debounced
export const RENDER_SETTINGS_SAVE_DEBOUNCE_MS = 400;
// Render Job polling: the backend hard-kills at 90s, so the UI gives up at 120s
export const RENDER_STATUS_POLL_INTERVAL_MS = 1000;
export const RENDER_STATUS_POLL_DEADLINE_MS = 120_000;

// Preview framing matches blender_studio.py so the preview frames like the render
export const PREVIEW_FRAME_MARGIN = 1.15;
// Blender's default studio angle (azimuth 45, elevation 28) in three.js (Y-up)
// coordinates: blender (x,y,z) maps to three (x,z,-y)
export const DEFAULT_VIEW_DIRECTION: [number, number, number] = [0.6243, 0.4695, -0.6243];
// Placeholder material for the lightweight preview; the real Render Settings
// color/roughness only apply to the Blender render
export const PREVIEW_MATERIAL_DEFAULTS = { color: "#1a1a1a", roughness: 0.3, metalness: 0 };
// Initial Canvas camera; PreviewScene re-frames to the model's bounds on load
export const PREVIEW_INITIAL_CAMERA: { position: [number, number, number]; near: number; far: number } = {
  position: [3, 2.3, -3],
  near: 0.01,
  far: 1000,
};
