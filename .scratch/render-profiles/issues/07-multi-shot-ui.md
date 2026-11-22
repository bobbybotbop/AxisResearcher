# 07: Multi-shot UI: Rig Overview + POV strip + image grid

**What to build:** Multi Shot Mode in the UI. In the Profile Editor: a Shot Mode toggle; Multi reveals the Rig Overview — the main square three.js view showing the benchy with every rig camera's frustum and sight line wireframed — plus the preset library for one-click camera adds, per-camera azimuth/elevation editing, and a horizontal strip of small square POV thumbnails under the overview (framing-only lightweight previews; click selects the camera and highlights its frustum). The editor's Render button in Multi renders the selected camera only (one job). In the main Step 4 panel, a multi-shot profile shows a compact "Multi-shot: N cameras" summary with the angle list, and Render produces an N-image grid with per-image download buttons.

**Blocked by:** 05 (Profile Editor), 06 (Multi-shot Camera Rig in the backend)

**Status:** done

- [x] Editor Shot Mode toggle; Multi shows Rig Overview with wireframe frustums + sight lines for every rig camera
- [x] Cameras added from the 10 presets; per-camera azimuth/elevation editable; rig saved in the profile
- [x] POV thumbnail strip renders each camera's framing; click-to-select highlights its frustum; editor Render renders the selected camera only
- [x] Main panel: "Multi-shot: N cameras" summary for multi-shot profiles; Render → N-image grid with per-image download
- [x] `cd frontend && npm run build` passes

## Comments

Implemented on branch `ticket/07-multi-shot-ui` (commit 9e319d0), based on integration tip f20c85c; `git merge integration/render-profiles` reported "Already up to date" (no conflicts, no markers — grep clean).

- **Editor** (`frontend/src/components/RenderProfileEditor.tsx`): Shot Mode select (Single/Multi) in the settings panel; `shot_mode` + `rig` added to the settings wire (`wireFromUnknown` parses them, so they save/load with the profile through the existing Save paths). Multi reveals a Camera Rig panel: one-click adds from all 10 `RENDER_ANGLE_PRESETS`, per-camera azimuth (−360..360) / elevation (−90..90) numeric inputs, and per-camera remove. Selection state (`selectedCamera`) drives the frustum highlight and which camera renders.
- **Rig Overview** (`frontend/src/components/StudioRenderPreview.tsx`): new `rig` + `selectedCamera` props draw a `THREE.CameraHelper` wireframe frustum + a sight line per rig camera (selected = primary blue, others slate). Camera placement auto-frames like the render (bounding sphere + FOV + `PREVIEW_FRAME_MARGIN`); `rigCameraDirection()` (new in `frontend/src/constants/render.ts`) mirrors `blender_studio.py`'s az/el→position math with the blender→three (x,z,−y) mapping.
- **POV strip**: horizontal row of small square thumbnails under the overview, one per camera, each a lightweight `StudioRenderPreview` in the new `fixedCamera` mode (locked camera at the rig angle, no OrbitControls, no hint line). Click selects the camera. Editor Render in Multi POSTs `shot_mode=multi` + `rig=[selected camera]` — one job.
- **Step 4** (`frontend/src/components/ThreeDFileFinder.tsx`): flat settings + profile select now pick up `shot_mode`/`rig`. Multi-shot active profile shows "Multi-shot: N cameras — #1 az 0° el 0°, …". Render sends `shot_mode` + full `rig`, polls `/api/render-status` for `shots_completed`/`shots_total` ("Rendering shot 2 of 5 in Blender..."), and shows the N-image grid with per-image download buttons (images stream into the grid as shots complete).
- **Verification**: `npm install` + `npm run build` passes (vite, 13.35s); backend suite `pytest tests/ -q` — 199 passed. No frontend test framework exists, so UI verification is build + wiring review.
