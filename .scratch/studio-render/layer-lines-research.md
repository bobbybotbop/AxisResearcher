# Research: FDM 3D-Print Layer Lines in Headless Blender 3.6 (Cycles CPU)

## Question restated

The AxisResearcher studio render (`backend/render/blender_studio.py`) currently produces a
smooth glossy plastic part — a single Principled BSDF with Base Color + Roughness and smooth
shading. We want the render to read as a real FDM 3D print: visible horizontal **layer lines**
(the per-layer ridges, as on a printed 3DBenchy), not smooth injection-molded plastic.

**Research question:** What are the practical techniques in Blender 3.6 (Cycles, CPU-only,
headless via `bpy`) to add realistic FDM layer lines to a mesh, and what are the tradeoffs
(render time, realism, implementation complexity) of each?

Constraints from the pipeline:
- Cycles CPU, 48 samples, adaptive sampling (threshold 0.02), max 4 bounces, OIDN denoise.
- 1024px, ~10–25s render target (30s soft, 90s hard kill).
- Model normalized so largest dimension = 2.0 scene units, base on z=0.
- STL imports have **no UVs**.
- Smooth shading is forced on (`polygon.use_smooth = True`).

---

## Recommended approach

**Procedural bump via a Wave Texture (Bands, Z direction) → Bump node → Principled Normal.**
This is the right default for this pipeline:

- Cheapest option — pure shader, no geometry change, no extra samples, no memory growth.
  Render time is essentially unchanged from the current smooth render.
- Works on STL imports with no UVs by driving the Wave Texture from **Object/Generated
  coordinates** (Texture Coordinate node) or **Geometry Position** — no UV unwrap needed.
- Layer lines on a product-photo-scale render are a shading effect, not a silhouette effect;
  at 1024px with the model framed to fill the view, bump is enough to read as FDM.

The one realism gap is the **silhouette**: bump does not change geometry, so the stair-stepping
visible on the silhouette of a real print's curved surfaces will not appear. For a product photo
at this resolution that gap is acceptable. If silhouette stair-stepping becomes a hard
requirement later, escalate to true displacement (technique 2) — but that costs the Experimental
feature set + adaptive subdivision and a real render-time/memory hit.

---

## Technique 1 — Procedural bump (Wave Texture → Bump)  ✅ recommended

### What it is

A Wave Texture node generates parallel bands. Orient the bands perpendicular to Z (the print
axis), feed the Fac output into a Bump node's Height, and connect Bump Normal into the Principled
BSDF Normal input. The result is a shading-only ridged surface that looks like stacked layers.

### Exact Blender 3.6 node names (verified against the 3.6 manual)

- `ShaderNodeTexWave` — Wave Texture. Properties: `wave_type` (`'BANDS'`/`'RINGS'`),
  `bands_direction` (`'X'`/`'Y'`/`'Z'`/`'DIAGONAL'`), `wave_profile` (`'SIN'`/`'SAW'`).
  Inputs: Vector, Scale, Distortion, Detail, Detail Scale, Roughness, Phase Offset.
  Outputs: Color, Fac. If Vector is left unconnected it defaults to **Generated** coordinates.
  Source: <https://docs.blender.org/manual/en/3.6/render/shader_nodes/textures/wave.html>
- `ShaderNodeBump` — Bump. Inputs: Strength, Distance, Height, Normal. Output: Normal.
  Strength interpolates 0→full; Distance is a multiplier on the height value (this is the
  world-space depth of the groove). Source:
  <https://docs.blender.org/manual/en/3.6/render/shader_nodes/vector/bump.html>
- `ShaderNodeTexCoord` — Texture Coordinate. Outputs include **Generated** (0–1 over the
  undeformed bounding box) and **Object** (object-space). Generated needs no UVs, so it works
  on raw STL imports. Source:
  <https://docs.blender.org/manual/en/3.6/render/shader_nodes/input/texture_coordinate.html>
- `ShaderNodeNewGeometry` — Geometry. **Position** output is the shading-point position in
  **World Space** (all vector outputs are world space). Use this if you want layer spacing in
  absolute scene units independent of the object's bounding box. Source:
  <https://docs.blender.org/manual/en/3.6/render/shader_nodes/input/geometry.html>

### How it slots into `apply_material()`

The current function only sets Base Color + Roughness on the existing Principled BSDF. Add a
small node chain. Two coordinate options:

**Option A — Generated coordinates (simplest, scale-invariant):**

```python
def apply_material(model, color, roughness):
    # ... existing srgb_to_linear + material/bsdf setup ...

    nt = material.node_tree
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'          # layers stack along Z (print axis)
    wave.wave_profile = 'SIN'           # smooth ridges; 'SAW' for sharper layer edges
    wave.inputs["Scale"].default_value = 300.0   # layers per bounding-box axis (see params)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.003  # groove depth in scene units
    nt.links.new(tex_coord.outputs["Generated"], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
```

Caveat: Generated is 0–1 over the bounding box, so `Scale` is "bands across the whole model,"
not an absolute layer spacing. For a model normalized to 2.0 units tall, `Scale = 2.0 /
layer_spacing`. With 0.0067-unit spacing (0.2mm on a 60mm part) that's ~300. This couples the
Scale to the model's aspect ratio — fine because the model is always normalized to 2.0.

**Option B — World-space position (absolute, aspect-independent):**

```python
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    math_sin = nt.nodes.new("ShaderNodeMath")
    math_sin.operation = 'SINE'
    # multiply Z by 2*pi / spacing so SINE period == layer spacing
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 2.0 * math.pi / 0.0067   # ~938 rad per unit
    nt.links.new(geom.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mult.inputs[0])
    nt.links.new(mult.outputs[0], math_sin.inputs[0])
    nt.links.new(math_sin.outputs[0], bump.inputs["Height"])
```

This gives exact 0.0067-unit layer spacing regardless of bounding box, at the cost of two extra
math nodes. Because the model is always normalized to 2.0 units and sits on z=0, both options
land on the same visual result; **Option A is recommended** for simplicity.

### Render-time impact

Negligible. Bump is evaluated in the surface shader at the existing sample count; no extra
geometry, no extra BVH, no extra rays. Expect the render to stay in the current 10–25s band.

### Realism limits

- **Silhouette is unchanged.** Bump only perturbs the shading normal; the mesh edge stays
  perfectly smooth. The Blender manual is explicit: with bump, "Surface silhouettes will not be
  accurate and there will be no self-shadowing of the displacement." (Material Settings,
  Displacement Method → Bump Only:
  <https://docs.blender.org/manual/en/3.6/render/cycles/material_settings.html>)
- No self-shadowing between ridges — the grooves are a normal trick, so they don't cast shadows
  on each other. At this scale that's not visible.
- Very fine layers can alias / get denoised away (see Risks).

---

## Technique 2 — True displacement (shader displacement + subdivision)

### What it is

Feed the same Wave/height pattern into a **Displacement node** → Material Output **Displacement**
input, and set the material's Displacement Method to actually move geometry. This produces real
ridges that appear on the silhouette and self-shadow.

### Exact Blender 3.6 names (verified)

- `ShaderNodeDisplacement` — Displacement node. Inputs: Height, Midlevel, Scale, Normal;
  property `space` (`'OBJECT'`/`'WORLD'`). Output: Displacement → Material Output Displacement
  input. "For best results the mesh must be subdivided finely." Source:
  <https://docs.blender.org/manual/en/3.6/render/shader_nodes/vector/displacement.html>
- Material Output node Displacement input: "Used to create bump mapping or actual subdivided
  displacement." Source:
  <https://docs.blender.org/manual/en/3.6/render/shader_nodes/output/material.html>
- Material setting Displacement Method (bpy `material.displacement_method`, enum `'BUMP'` /
  `'DISPLACEMENT'` / `'BOTH'`; UI labels "Bump Only" / "Displacement Only" /
  "Displacement and Bump"). "Displacement Only ... gives the best quality results, if the mesh is
  finely subdivided ... also the most memory intensive." Source:
  <https://docs.blender.org/manual/en/3.6/render/cycles/material_settings.html>

### The catch: subdivision is required, and in 3.6 it is Experimental

Real displacement only moves existing vertices, so the mesh must be finely subdivided. The
efficient way, Adaptive Subdivision (OpenSubdiv micropolygons, dicing near the camera), is gated
behind the Experimental Feature Set in Blender 3.6:

- "Adaptive Subdivision ... When using the Experimental Feature Set the Subdivision Surface
  Modifier gets changed to control the subdivision of a mesh at the time of rendering."
  <https://docs.blender.org/manual/en/3.6/render/cycles/object_settings/adaptive_subdiv.html>
- "Experimental features are disabled / hidden by default ... set Feature Set to Experimental ...
  Adaptive subdivision is currently the only experimental feature."
  <https://docs.blender.org/manual/en/3.6/render/cycles/features.html>

In bpy: `scene.cycles.feature_set = 'EXPERIMENTAL'`, then a Subdivision Surface modifier gains
adaptive dicing controls (Dicing Scale). Without the experimental set you would need a brute-force
high-level Subdivision Surface modifier, which balloons memory on a dense STL.

### Render-time impact

Significant. Micropolygon tessellation plus a much larger BVH plus finer shading samples. The
manual calls Displacement Only "the most memory intensive" method. On CPU with a 30s soft target
this is a real risk; expect to blow the budget on all but small models, and it needs the
Experimental feature set, which the manual warns "might be broken or change in the future."

### Realism

Highest: true silhouette stair-stepping and inter-ridge self-shadowing. Only worth it if the
silhouette is a hard requirement.

---

## Technique 3 — Displace modifier (geometry displacement, pre-render)

### What it is

A Displace modifier deforms the mesh vertices directly using a procedural texture, before render.
True geometry, so it affects the silhouette without needing the Experimental feature set.

### Exact Blender 3.6 names (verified)

- Displace modifier (`bpy.types.DisplaceModifier`). Options: Texture, Coordinates, Direction
  (X/Y/Z/Normal/Custom Normal/RGB to XYZ), Space, Strength, Midlevel, Vertex Group.
  `vertex_offset = (texture_value - Midlevel) x Strength`. Source:
  <https://docs.blender.org/manual/en/3.6/modeling/modifiers/deform/displace.html>

### Why it is the wrong fit

- It displaces existing vertices only, so it needs a Subdivision Surface modifier in front of it
  anyway, with the same memory cost as technique 2 but no adaptive dicing to control it.
- The procedural texture types available to modifiers (Clouds, Marble, Wood, etc.) do not include
  a clean horizontal-bands primitive; you would have to fake bands from Marble/Wood or an image
  texture. A Wave pattern is far easier in the shader.
- It bakes displacement at a fixed mesh resolution, with no per-pixel dicing.

Verdict: more complexity and memory than shader displacement, less control, same subdivision
requirement. Not recommended.

---

## Technique 4 — Voronoi / Noise alternatives

The Wave Texture is the correct primitive for fine parallel ridges. Voronoi produces cellular pits
and Noise produces organic bumps; neither reads as stacked layers. The Wave Texture manual notes
its built-in Distortion uses a Noise Texture Color output to warp the bands
(<https://docs.blender.org/manual/en/3.6/render/shader_nodes/textures/wave.html>); a small
Distortion value (1-3) can add realistic slight layer wobble without breaking the parallel
structure. The base shape must be Wave Bands, not Voronoi/Noise.

---

## Concrete starting parameters

Derived from the layer-height math: a 0.2mm layer on a ~60mm part, with the model normalized to
2.0 scene units tall, gives layer spacing of about 0.2/60 x 2.0 = 0.0067 scene units. The manual
gives no canonical numbers, so these are reasoned starting points to tune against a reference
photo:

| Parameter | Node / input | Starting value | Notes |
|---|---|---|---|
| Layer spacing | — | 0.0067 units | 0.2mm on 60mm part. Thicker (0.01) = more visible. |
| Wave Scale (Generated) | Wave Texture, Scale | ~300 | = 2.0 / 0.0067. Bands across the 2.0-unit bbox. |
| Wave profile | Wave Texture, Wave Profile | SIN | SAW for a sharper, more extruded edge. |
| Wave distortion | Wave Texture, Distortion | 0-3 | Slight wobble; keep low to preserve parallel lines. |
| Bump Strength | Bump, Strength | 0.3-0.5 | Interpolates 0 to full; start mid and tune. |
| Bump Distance | Bump, Distance | 0.002-0.004 | Groove depth in scene units; ~half the spacing. |

At 1024px with the model filling the frame, 0.0067-unit spacing is roughly 3-4 px per layer:
visible but fine. If lines are too subtle, raise Bump Distance before Strength (Distance is the
physical depth; Strength just fades the effect).

---

## Risks / gotchas

- OIDN denoiser can blur fine bump detail. The sampling manual recommends Albedo + Normal input
  passes because "None can blur out details, especially at lower sample counts," and the Prefilter
  "Accurate" option "usually produces more detailed results than Fast."
  (<https://docs.blender.org/manual/en/3.6/render/cycles/render_settings/sampling.html>)
  At 48 samples the layer lines are high-frequency shading detail, exactly what an aggressive
  denoiser smooths. Mitigation: keep Bump Distance modest; if lines wash out, raise samples or
  check the denoiser input-pass/prefilter settings.
- Adaptive sampling threshold 0.02 may stop sampling before the fine ridges converge, leaving them
  to the denoiser. Same mitigation as above.
- Smooth shading interaction. The script forces `polygon.use_smooth = True`. Bump perturbs the
  smooth shading normal, which is what we want; but on a low-poly STL the underlying smooth normal
  interpolation can make bands look wavy on large flat triangles. Generated-coordinate bands are
  independent of tessellation, so this is usually fine; if banding follows triangle edges, the mesh
  needs more geometry, not more bump.
- White-sweep compositor clipping. `setup_white_compositor()` pushes anything above ~0.85 linear
  toward pure white. Layer-line highlights on a glossy dark part are unlikely to cross that
  threshold (the model albedo is dark), so the ridges on the model body survive; only specular
  hotspots could clip, and those are already clipped today. Low risk, but verify on a light-colored
  render.
- Bump Distance vs. scale. Because the model is always normalized to 2.0 units, a fixed Bump
  Distance is consistent across models; but a fixed Generated-space Wave Scale is only correct
  because the height is always 2.0. If normalization ever changes, recompute Scale.

---

## Sources

- Wave Texture node: <https://docs.blender.org/manual/en/3.6/render/shader_nodes/textures/wave.html>
- Bump node: <https://docs.blender.org/manual/en/3.6/render/shader_nodes/vector/bump.html>
- Texture Coordinate node (Generated/Object, no UVs needed): <https://docs.blender.org/manual/en/3.6/render/shader_nodes/input/texture_coordinate.html>
- Geometry node (Position is World Space): <https://docs.blender.org/manual/en/3.6/render/shader_nodes/input/geometry.html>
- Displacement node: <https://docs.blender.org/manual/en/3.6/render/shader_nodes/vector/displacement.html>
- Material Output node (Displacement input): <https://docs.blender.org/manual/en/3.6/render/shader_nodes/output/material.html>
- Cycles Material Settings, Displacement Method (bump vs displacement, silhouette/memory): <https://docs.blender.org/manual/en/3.6/render/cycles/material_settings.html>
- Adaptive Subdivision (requires Experimental Feature Set): <https://docs.blender.org/manual/en/3.6/render/cycles/object_settings/adaptive_subdiv.html>
- Experimental Features (adaptive subdivision is the only one; may be unstable): <https://docs.blender.org/manual/en/3.6/render/cycles/features.html>
- Displace modifier: <https://docs.blender.org/manual/en/3.6/modeling/modifiers/deform/displace.html>
- Cycles Sampling / Denoising (OIDN on CPU, input passes, prefilter): <https://docs.blender.org/manual/en/3.6/render/cycles/render_settings/sampling.html>
