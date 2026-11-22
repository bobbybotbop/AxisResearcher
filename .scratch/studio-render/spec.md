# Spec: Step 4 — Studio Render (3D File Finder)

Locked design from the grill-with-docs session. Domain terms live in `GLOSSARY.md` (Studio Render, Render Job, Render Settings, Render Mesh, Camera Intent); rationale in `docs/adr/0001-studio-render-pipeline.md`. Read both before implementing.

## What Step 4 is

A fourth panel in the 3D File Finder wizard that renders the model downloaded in Step 3 into an Amazon-style product photo: pure white background, soft grounding shadow, slightly glossy plastic (default near-black), one camera angle chosen by the user from a live preview.

## Locked decisions

- **Renderer**: headless Blender 3.6.1 via subprocess (`--background --python <script> -- args`), exe path configurable (installed at `C:\Program Files\Blender Foundation\Blender 3.6\blender.exe`, not on PATH). **Cycles, CPU-only** — no GPU mode at all.
- **Scene**: white sweep + shadow-catcher ground (soft contact shadow, background blown to pure 255 white), 3-point area-light rig, fixed exposure. Single Principled BSDF; user color (default near-black #1a1a1a) + roughness (default ~0.3). Model auto-centered and scaled to standard size; camera placed at user's direction + FOV with distance auto-computed to frame the whole model.
- **Performance**: ~64–128 samples + adaptive sampling + OIDN denoising; target 10–25s at 1024² on the Ryzen 9 5900HS. 30s is a soft target; 90s hard kill as hang protection.
- **Render Job**: multipart POST `/api/render` (file + settings + camera position/target/FOV) → `{task_id}`; frontend polls `/api/render-status/<task_id>`. Mirror the existing `/api/generate-images` task-id + polling pattern (see `app.py` around the `image_generation_lock` dict + `GET /api/generate-images-status/<task_id>`).
- **Render Mesh**: `.stl`/`.obj`/`.ply` used as-is. `.step`/`.stp` → STL via the `gmsh` pip package; `.3mf` → STL via `trimesh` (both verified working on this machine; trimesh needs `networkx` + `lxml` alongside). `.amf` is unsupported everywhere: removed from preferred extensions, rejected with a clear error in the download step.
- **Preview**: three.js (`three`, `@react-three/fiber`, `@react-three/drei` — none installed yet) viewport with orbit controls + FOV slider (20–80°, default 40°). Zips unpacked client-side with the already-installed JSZip; best file auto-picked by the existing ranking, dropdown to switch when multiple candidates exist.
- **Camera Intent**: on Render, frontend sends camera position + look-at target + FOV. Backend converts three.js (Y-up) to Blender (Z-up) coordinates and auto-frames. Render must match the preview's angle.
- **Render Settings**: persisted in `listingPreferences.json` via the existing `get/save_*_settings` pattern in `backend/copyScripts/combine_data.py` + a `/api/render-settings` GET/POST route. Persisted: color, glossiness, resolution, FOV. Ephemeral: camera angle.
- **Controls panel**: color picker, glossiness slider, square-resolution dropdown (512²/1024²/2048², default 1024²), FOV slider. Lighting/exposure/background are fixed, not exposed.
- **Output**: saved as `generated-images/generated_render_<YYYYMMDD_HHMMSS>.png` (mirror the existing naming convention), shown in the panel with a download button. Listing integration is out of scope.
- **Errors**: friendly panel errors for unsupported format (`.amf`), conversion failure, missing Blender, render timeout.

## Key integration facts (from codebase exploration)

- Wizard: `frontend/src/components/ThreeDFileFinder.tsx` — three stacked step panels; Step 4 is a fourth panel in the same card style. Step 3's result bytes live only in the browser (download or File System Access API); Step 4 re-uploads the blob with the render request.
- Backend: single-file Flask in `app.py`, routes as module-level `@app.route('/api/...')`; helpers in `backend/`; dirs from `backend/constants/paths.py` (`GENERATED_IMAGES_DIR` etc.). Vite dev server (port 4000) proxies `/api` → Flask (port 5000).
- Preferred 3D extensions ranking: `backend/constants/files_3d.py` (`PREFERRED_3D_EXTENSIONS`); best-file-from-zip logic: `backend/downloaders/zip_utils.py:extract_best_3d_file`.
- Frontend stack: React 18 + Vite 5 + TS, Tailwind 4. `jszip` already installed.
- Settings pattern: `backend/copyScripts/combine_data.py` `load_config()/save_config()` + per-setting `get/save_*` pairs.
- Download route for Step 3: `POST /api/download-3d-file` in `app.py`.

## Verification

- `cd frontend && npm run build` passes
- `python -m pytest tests/` passes
- End-to-end: Step 3 download → Step 4 preview → Render → image in panel within ~30s
