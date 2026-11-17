# Glossary

## 3D File Finder
The multi-step wizard (in `ThreeDFileFinder.tsx`) that goes from an eBay photo to a downloaded 3D printable model: Step 1 fetch eBay photos, Step 2 reverse image search, Step 3 download the 3D file, Step 4 Studio Render.

## Studio Render (Step 4)
The fourth step of the 3D File Finder: renders the downloaded 3D model into a professional product photo — pure white background, soft grounding shadow, "Amazon hero shot" look — via headless Blender on the backend. Exactly one camera angle per render (for now).

## Render Job
An asynchronous unit of work: the frontend submits a render request (model file + settings + camera), receives a task id, and polls for completion. Mirrors the existing `/api/generate-images` task-id pattern.

## Render Settings
The user-configurable inputs to a Studio Render, persisted in `listingPreferences.json`: material (color, glossiness, Surface Finish), lighting (key/fill/rim intensities, ambient strength), shadows (on/off, softness), exposure, square resolution, field of view, and Shot Mode with its Camera Rig. Background is fixed pure white; light positions and color management are fixed. Rendering is CPU-only (Cycles); there is deliberately no GPU mode — this machine has only an integrated AMD GPU, which Cycles cannot use.

## Render Profile
A named snapshot of the full Render Settings, saved in `listingPreferences.json` under `render_profiles`. The always-present default entry is "Current Settings" — the flat settings themselves. Selecting a profile in Step 4 copies its values into Current Settings (the selection is sticky), so the render path always reads the flat settings regardless of profiles. Profiles are created and edited in the Profile Editor; editing "Current Settings" writes back to the flat settings.

## Profile Editor
The in-place editor view within Step 4 (not a route, not a floating modal) for creating or editing a Render Profile: a square 3D viewer preloaded with a bundled 3DBenchy, a settings panel to its right, a Render button that runs a real Blender Render Job on the benchy with the editor's current values, and Save / "Save as new profile" buttons. "Save as new profile" opens a name-input modal; in edit mode "Save" overwrites the profile in place.

## Surface Finish
The material texture of a Studio Render: Smooth Plastic (plain Principled BSDF) or Layer Lines (procedural FDM layer-line bump). Layer Lines exposes two sub-settings: layer height (labeled in real FDM layer heights, 0.08–0.4mm, default 0.2mm) and line depth (bump strength).

## Shot Mode
Single (one camera angle per render, captured ephemerally from the Step 4 preview — today's behavior) or Multi (a Camera Rig of N cameras producing N images per Render click, run as sequential Render Jobs and shown as an image grid). Shot Mode and the rig are saved in the Render Profile.

## Camera Rig
The ordered set of cameras in Multi Shot Mode. Each camera is defined by azimuth (orbit around the model, 0–360°) and elevation (height, −90° to +90°); roll is fixed at 0 (horizon always level) and distance/look-at stay automatic. A preset library of named angles (front, top, left, right, bottom, back, front-right, back-left, front-top-left, back-bottom-right) provides one-click starting points.

## Rig Overview
In the Profile Editor's Multi Shot Mode, the main square three.js view showing the benchy with every rig camera's frustum and sight line wireframed. Below it, a strip of small per-camera POV thumbnails (framing-only lightweight previews) — clicking one selects that camera for editing and highlights its frustum.

## Render Mesh
The single canonical mesh both the Step 4 preview and the Blender render work from. Downloaded files in formats Blender 3.6 imports natively (.stl, .obj, .ply) are used as-is; .step/.stp are normalized to .stl with gmsh (pip wheel) and .3mf with trimesh (pure-Python pip package) — both are project dependencies, not machine installs — guaranteeing the preview and the render always show the same geometry. .amf files are not supported at all: they are excluded from the preferred download extensions and rejected with a clear ".amf is not supported" error already in the download step.

## Camera Intent
The camera state captured from the Step 4 live preview when the user presses Render: viewing direction, look-at target, and field of view. The backend reproduces the *direction and FOV* but auto-computes the distance so the whole model is always framed, regardless of the model's original scale or origin.
