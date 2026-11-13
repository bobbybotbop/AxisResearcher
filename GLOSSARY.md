# Glossary

## 3D File Finder
The multi-step wizard (in `ThreeDFileFinder.tsx`) that goes from an eBay photo to a downloaded 3D printable model: Step 1 fetch eBay photos, Step 2 reverse image search, Step 3 download the 3D file, Step 4 Studio Render.

## Studio Render (Step 4)
The fourth step of the 3D File Finder: renders the downloaded 3D model into a professional product photo — pure white background, soft grounding shadow, "Amazon hero shot" look — via headless Blender on the backend. Exactly one camera angle per render (for now).

## Render Job
An asynchronous unit of work: the frontend submits a render request (model file + settings + camera), receives a task id, and polls for completion. Mirrors the existing `/api/generate-images` task-id pattern.

## Render Settings
The user-configurable inputs to a Studio Render, persisted in `listingPreferences.json`: model color (default near-black), glossiness, square resolution (dropdown of common sizes), and field of view. Lighting rig, exposure, and background are a fixed preset, not user settings. Rendering is CPU-only (Cycles); there is deliberately no GPU mode — this machine has only an integrated AMD GPU, which Cycles cannot use.

## Render Mesh
The single canonical mesh both the Step 4 preview and the Blender render work from. Downloaded files in formats Blender 3.6 imports natively (.stl, .obj, .ply) are used as-is; .step/.stp are normalized to .stl with gmsh (pip wheel) and .3mf with trimesh (pure-Python pip package) — both are project dependencies, not machine installs — guaranteeing the preview and the render always show the same geometry. .amf files are not supported at all: they are excluded from the preferred download extensions and rejected with a clear ".amf is not supported" error already in the download step.

## Camera Intent
The camera state captured from the Step 4 live preview when the user presses Render: viewing direction, look-at target, and field of view. The backend reproduces the *direction and FOV* but auto-computes the distance so the whole model is always framed, regardless of the model's original scale or origin.
