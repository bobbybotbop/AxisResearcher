# 02: Tracer bullet — fixed-angle render, end to end

**What to build:** A minimal Step 4 "Studio Render" panel in the 3D File Finder wizard with a single Render button. Pressing it uploads the model file from Step 3 (native formats only: `.stl`/`.obj`/`.ply`) to a new render endpoint, which runs headless Blender as a background Render Job (task-id + polling, mirroring the existing generate-images pattern) and renders the model with the fixed studio scene from the spec: white sweep, shadow-catcher ground, 3-point area lights, near-black slightly-glossy material, 1024x1024, fixed camera angle with auto-framing. The finished image appears in the panel with a download button, saved server-side under the generated-images dir as `generated_render_<timestamp>.png`. Backend pip deps (`gmsh`, `trimesh`, `networkx`, `lxml`) and the configurable Blender exe path land here, as does the Blender render script. Errors (missing Blender, render failure, unsupported format for now) show as friendly panel errors.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] A fourth Studio Render panel exists in the wizard with a Render button, enabled once a model is available from Step 3
- [ ] Pressing Render uploads the model and starts a Render Job; the panel shows progress while polling and then displays the rendered image
- [ ] The render is a recognizable studio product shot: white background, soft contact shadow, glossy near-black model, whole model framed
- [ ] The image is saved server-side with the `generated_render_<timestamp>` naming convention and downloadable from the panel
- [ ] Blender path is configurable; a missing Blender produces a friendly error, not a stack trace
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
