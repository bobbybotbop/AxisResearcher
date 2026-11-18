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
// roughness (glossiness = 1 − roughness). Lighting/shadow/exposure defaults
// reproduce the original hardcoded rig exactly.
export const RENDER_SETTINGS_DEFAULTS = {
  color: "#1a1a1a",
  roughness: 0.3,
  resolution: 1024,
  fov: 40,
  finish: "smooth" as RenderFinish,
  layerHeightMm: 0.2,
  layerDepth: 0.4,
  keyEnergy: 150,
  fillEnergy: 60,
  rimEnergy: 250,
  ambient: 0.35,
  shadow: true,
  shadowSoftness: 1.5,
  exposure: 1.0,
};
export type RenderFinish = "smooth" | "layer-lines";
export const RENDER_FINISH_OPTIONS: { value: RenderFinish; label: string }[] = [
  { value: "smooth", label: "Smooth Plastic" },
  { value: "layer-lines", label: "Layer Lines" },
];
export const RENDER_LAYER_HEIGHT_MM_MIN = 0.08;
export const RENDER_LAYER_HEIGHT_MM_MAX = 0.4;
export const RENDER_ENERGY_MAX = 2000;
export const RENDER_AMBIENT_MAX = 2;
export const RENDER_SHADOW_SOFTNESS_MIN = 0.1;
export const RENDER_SHADOW_SOFTNESS_MAX = 10;
export const RENDER_EXPOSURE_MIN = 0.1;
export const RENDER_EXPOSURE_MAX = 4;
export const RENDER_RESOLUTION_OPTIONS = [512, 1024, 2048];
export const RENDER_FOV_MIN = 20;
export const RENDER_FOV_MAX = 80;

// Slider/color inputs fire many events while dragging; persist debounced
export const RENDER_SETTINGS_SAVE_DEBOUNCE_MS = 400;

// Shot Mode + Camera Rig, mirrors backend/constants/render.py. Multi runs the
// rig as N sequential Render Jobs (Cycles CPU saturates the machine).
export type RenderShotMode = "single" | "multi";
export const RENDER_SHOT_MODE_OPTIONS: { value: RenderShotMode; label: string }[] = [
  { value: "single", label: "Single" },
  { value: "multi", label: "Multi" },
];
export const DEFAULT_RENDER_SHOT_MODE: RenderShotMode = "single";
// One rig camera: azimuth (orbit, degrees) + elevation (height, -90..+90);
// roll fixed 0, distance/look-at automatic
export interface RenderRigCamera {
  azimuth: number;
  elevation: number;
}
// Named one-click rig angles, mirrors backend RENDER_ANGLE_PRESETS
export const RENDER_ANGLE_PRESETS: Record<string, RenderRigCamera> = {
  front: { azimuth: 0, elevation: 0 },
  top: { azimuth: 0, elevation: 89 },
  left: { azimuth: -90, elevation: 0 },
  right: { azimuth: 90, elevation: 0 },
  bottom: { azimuth: 0, elevation: -89 },
  back: { azimuth: 180, elevation: 0 },
  "front-right": { azimuth: 45, elevation: 0 },
  "back-left": { azimuth: 225, elevation: 0 },
  "front-top-left": { azimuth: -45, elevation: 45 },
  "back-bottom-right": { azimuth: 135, elevation: -45 },
};

// Render Profiles (named snapshots of the full Render Settings). The settings
// object is opaque here on purpose: the dropdown copies whatever the profile
// contains verbatim into the flat settings, so new fields need no UI changes.
export type RenderProfileSettings = Record<string, unknown>;
export interface RenderProfilesResponse {
  profiles: Record<string, RenderProfileSettings>;
  active: string | null; // null = "Current Settings" (the flat settings), never a stored profile
}
// Label of the implicit default entry (active=null) in the profile dropdown
export const CURRENT_SETTINGS_LABEL = "Current Settings";
// Render Job polling: the backend hard-kills at 90s, so the UI gives up at 120s
export const RENDER_STATUS_POLL_INTERVAL_MS = 1000;
export const RENDER_STATUS_POLL_DEADLINE_MS = 120_000;

// Rig camera azimuth/elevation → three.js (Y-up) unit direction, mirroring
// blender_studio.py's add_camera: blender (x,y,z) maps to three (x,z,-y), so
// (cos(el)cos(az), cos(el)sin(az), sin(el)) becomes (cos(el)cos(az), sin(el), -cos(el)sin(az)).
export const rigCameraDirection = (azimuth: number, elevation: number): [number, number, number] => {
  const az = (azimuth * Math.PI) / 180;
  const el = (elevation * Math.PI) / 180;
  return [Math.cos(el) * Math.cos(az), Math.sin(el), -Math.cos(el) * Math.sin(az)];
};

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
