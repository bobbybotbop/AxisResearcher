# Studio Render (Step 4) pipeline decisions

The 3D File Finder's Step 4 renders the downloaded model to an Amazon-style product photo via headless Blender 3.6 (Cycles) on the backend. Three decisions were made that contradict the obvious path:

1. **CPU-only Cycles, no GPU mode.** The original spec asked for an NVIDIA GPU toggle, but the target machine has only an integrated AMD Radeon GPU, which Cycles cannot use (no CUDA/OptiX; HIP on iGPUs is unreliable). Rather than ship a dead toggle or a second engine (Eevee) with divergent output, rendering is CPU-only. The 30-second budget is a soft target met via low samples (64–128), adaptive sampling, and OIDN denoising — viable because renders are always a single uniform-color object on a white background, which denoises extremely well. A 90s hard kill exists only as hang protection.

2. **In-project pip converters, not machine-installed tools.** Non-native formats are normalized to `.stl` in the Flask process before Blender sees them: `.step`/`.stp` via the `gmsh` pip wheel (bundles OpenCASCADE), `.3mf` via `trimesh` (pure Python). Both were verified working on the target machine (STEP→STL and 3MF→STL round-trips). PrusaSlicer's CLI (present on the machine) was rejected so deployment depends only on `requirements.txt`, not on what happens to be installed. Blender itself remains the one external install.

3. **`.amf` rejected outright.** No lightweight importable decoder exists (trimesh supports AMF export only). `.amf` is removed from the supported 3D-file extensions, and the download step raises a clear ".amf is not supported" error if one appears, rather than failing obscurely at render time.

## Consequences

- The preview and the render always operate on the same canonical Render Mesh, so WYSIWYG holds by construction.
- Swapping in GPU rendering later means adding one engine toggle; the scene/script structure does not change.
- If `.amf` files ever become common in downloads, supporting them requires a hand-rolled XML parser or a heavier dependency.
