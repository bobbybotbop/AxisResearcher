# 04: Format normalization to Render Mesh

**What to build:** Uploads in `.step`/`.stp` and `.3mf` are normalized to STL server-side before use: `.step`/`.stp` via the `gmsh` pip package, `.3mf` via `trimesh`. The converted STL (the Render Mesh) is returned to the browser so the live preview shows it, and the same converted mesh is what Blender renders — preview and render always show identical geometry. Conversion failures surface as friendly panel errors. Native formats (`.stl`/`.obj`/`.ply`) continue to pass through unconverted.

**Blocked by:** 03 (Live preview + Camera Intent).

**Status:** ready-for-agent

- [ ] A `.3mf` upload previews and renders correctly (converted via trimesh)
- [ ] A `.step`/`.stp` upload previews and renders correctly (converted via gmsh)
- [ ] Preview and render operate on the same converted mesh
- [ ] A corrupt or unconvertible file produces a friendly error in the panel, not a stack trace
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
