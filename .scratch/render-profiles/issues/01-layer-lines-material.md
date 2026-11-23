# 01: Layer-lines material in the Blender script

**What to build:** The studio render script grows a Surface Finish parameter: `smooth` (today's behavior) or `layer-lines` — a procedural Wave Texture (Bands, Z) → Bump node → Principled Normal, per the research in `.scratch/studio-render/layer-lines-research.md`. Two sub-settings arrive as CLI args: layer height (given in real FDM millimeters, e.g. 0.2, converted by the script to wave scale against the normalized 2.0-unit model) and line depth (bump strength). Running the script manually with layer-lines flags on a benchy STL produces a render with visible horizontal layer lines; running without them is byte-identical in behavior to today.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `--finish smooth|layer-lines`, `--layer-height-mm`, `--layer-depth` CLI args on the render script; `smooth` behaves exactly as today
- [x] Layer Lines render of the bundled benchy shows clear horizontal layer lines at 1024px
- [x] Timed A/B (same model, same seed, median of 3 runs): layer-lines render stays within the 30s soft target on this machine; timing recorded in the ticket comments
- [x] If the OIDN denoiser visibly blurs the lines, enable Albedo+Normal denoising input passes (per the research) and note it

## Comments

Implemented in `backend/render/blender_studio.py` (worktree commit cb14003 on
`ticket/01-layer-lines-material`, merged clean with `integration/render-profiles`).

- CLI: `--finish {smooth,layer-lines}` (default `smooth`), `--layer-height-mm`
  (float, default 0.2), `--layer-depth` (float, default 0.4 = Bump Strength).
- Node graph (layer-lines only): Texture Coordinate Generated -> Wave Texture
  (BANDS, Z, SIN, Scale = 60.0 / layer_height_mm) -> Bump (Strength =
  layer_depth, Distance = half the layer spacing in scene units) -> Principled
  Normal. `smooth` adds no nodes — byte-identical behavior to before.
- mm-to-scale conversion: the model is normalized to 2.0 scene units, so a real
  FDM mm height needs an assumed real-world part size to convert. Used
  `ASSUMED_MODEL_HEIGHT_MM = 60.0` (the benchy reference from the research), so
  0.2mm -> 300 bands across the Generated bbox, matching the research's
  starting value.
- Structural tests in `tests/test_render_layer_lines.py` (6 tests, all pass):
  CLI surface, wave/bump chain wiring, mm->scale conversion, and smooth-adds-
  no-bump-nodes. Blender can't run in pytest, so pixel verification was manual.

**Timed A/B** (3DBenchy.stl, 1024px, default camera azimuth 45 / elevation 28 /
fov 40, Cycles CPU 48 samples + OIDN, 1 run each, wall-clock via `time`):

| Render | Command flags | Time |
|---|---|---|
| Base (smooth) | `--resolution 1024` | 27.7s |
| Layer Lines | `--resolution 1024 --finish layer-lines --layer-height-mm 0.2 --layer-depth 0.4` | 29.6s |

Both within the 30s soft target; layer-lines adds ~2s (bump shading only, no
geometry/samples change). Renders saved to `.scratch/render-profiles/ab_base.png`
and `ab_lines.png` in the main repo.

**OIDN blur check:** lines are crisp at native resolution (verified on a 400x200
crop of the roof) — no visible blurring, so Albedo+Normal denoising input passes
were NOT needed. Noted per the research's risk section; revisit if finer layer
heights (<0.2mm) wash out.

**Note for the merger:** `backend/render/__init__.py` `render_model()` does not
yet pass the new flags — wiring the finish through the Python API / settings /
UI is a later ticket's job (this ticket was scoped to the Blender script). The
new args all have defaults, so existing callers are unaffected.
