# 03: Live preview + Camera Intent

**What to build:** The Studio Render panel gains a live three.js viewport (new deps: `three`, `@react-three/fiber`, `@react-three/drei`). The Step 3 model previews with orbit controls and an FOV slider (20–80°, default 40°). If Step 3 produced a zip, it is unpacked client-side with JSZip, the best model auto-picked by the existing extension ranking, and a dropdown lets the user switch between multiple candidate models. When the user presses Render, the camera's position, look-at target, and FOV are sent with the render request; the backend converts three.js (Y-up) to Blender (Z-up) coordinates, places the camera at that direction and FOV, and auto-computes the distance to frame the whole model. The render matches the angle the user framed in the preview.

**Blocked by:** 02 (Tracer bullet — fixed-angle render, end to end).

**Status:** ready-for-agent

- [ ] The panel shows a live 3D preview of the Step 3 model (stl/obj/ply) with orbit controls and an FOV slider
- [ ] Zip downloads unpack client-side; best model auto-selected; dropdown appears when multiple candidate models exist and switches the preview
- [ ] Rendering from a user-chosen angle produces an image from that same angle (direction + FOV match; framing auto-adjusted so the whole model is visible)
- [ ] Preview and render show the same model orientation
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
