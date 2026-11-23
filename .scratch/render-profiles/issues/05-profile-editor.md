# 05: Profile Editor (single-shot)

**What to build:** The Profile Editor (GLOSSARY.md) replaces the Step 4 panel content in place (not a route, not a floating modal): a square 3D viewer preloaded with the bundled benchy (`frontend/public/render/3DBenchy.stl`), a settings panel to its right exposing the full settings surface (material incl. Surface Finish dropdown with layer-height/line-depth sub-settings, key/fill/rim, ambient, shadow on/off + softness, exposure, resolution, FOV), a Render button that runs a real Blender Render Job on the benchy with the editor's current values and shows the result in the viewer, and Save / "Save as new profile" buttons. "Save as new profile" opens a name-input modal; confirm persists via the profiles API. In edit mode "Save" overwrites the profile in place (no modal); editing "Current Settings" writes back to the flat settings. The old inline settings row is fully removed — the dropdown + editor is the single editing surface. A back path returns to the dropdown view.

**Blocked by:** 02 (Expanded settings end-to-end), 04 (Profile dropdown in Step 4)

**Status:** done

- [x] Editor opens from dropdown Edit / Create-new with the benchy preloaded in a square viewer; settings panel on the right
- [x] Render button produces a real Blender render of the benchy with the editor's values, shown in the panel
- [x] Save-as-new → name modal → confirm → profile appears in the dropdown; Save in edit mode overwrites in place
- [x] Editing "Current Settings" saves to the flat settings
- [x] The old inline settings row is gone; `cd frontend && npm run build` passes

## Comments

- Built `frontend/src/components/RenderProfileEditor.tsx`: square (aspect-square) benchy viewer via `StudioRenderPreview` (new optional `square` prop), full settings panel to the right (color, glossiness, Surface Finish dropdown + layer-height/line-depth when layer-lines, key/fill/rim, ambient, exposure, shadow on/off + softness, resolution, FOV), a Render button running a real Blender Render Job on the bundled benchy (multipart `/api/render` + `/api/render-status/<task_id>` polling, same pattern as Step 4), and Save buttons.
- The editor edits a LOCAL copy of the settings — sliders never persist directly. Only Save writes: "Current Settings" (editingProfile=null) → `POST /api/render-settings`; a named profile → `POST /api/render-profiles/<name>` (overwrite, no modal); "create" → name-input modal → `POST /api/render-profiles`. A "Save as new profile" secondary button is also offered in edit/current mode (per GLOSSARY "Save / 'Save as new profile' buttons"). Initial values load from `/api/render-settings` for "create"/null, from `/api/render-profiles` for a named profile. After a Current Settings save the parent reloads the flat settings (`onSavedCurrentSettings`) so Step 4 reflects them.
- Wired into `ThreeDFileFinder.tsx` Step 4 replacing the placeholder block; back path returns to the dropdown. The old inline settings row is fully removed (it was already gone on ticket 04's side; ticket 02's merge had resurrected it via conflict markers).
- IMPORTANT for the merger: the integration tip `fa5a6b0` (Merge ticket 02) had **conflict markers committed into `ThreeDFileFinder.tsx`**. Resolved by keeping ticket 04's dropdown+editor structure with ticket 02's expanded settings state/logic and dropping the old inline row. (A concurrent fix `c0c5646` landed on integration during this work; the final merged state is clean — verified zero `<<<<<<<` markers.)
- The bundled benchy `frontend/public/render/3DBenchy.stl` is gitignored (`*.stl` in .gitignore) — it exists in the main checkout and was copied into this worktree, but it is NOT committed. Any fresh checkout/worktree needs the file present at that path for the editor's viewer + Render button to work.
- Verified: `cd frontend && npm install && npm run build` passes; `npm run type-check` clean; `python -m pytest tests/` 164 passed. No backend changes were needed (the profiles/settings/render APIs from tickets 02–04 already cover everything).
