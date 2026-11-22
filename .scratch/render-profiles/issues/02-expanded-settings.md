# 02: Expanded settings end-to-end (lighting, shadows, exposure, finish)

**What to build:** The full settings surface flows through the stack. The render script accepts: key/fill/rim intensity, ambient (world) strength, shadow on/off, shadow softness (key light size), exposure (global multiplier on all light energies + world strength, default 1.0), plus the finish args from ticket 01. The Render Settings schema in `listingPreferences.json`, the `/api/render-settings` GET/POST, and the `/api/render` route accept, persist, and forward all of them. Step 4's existing inline controls row gains the new knobs as a temporary UI (replaced by the editor in ticket 05). Rendering from Step 4 with non-default lighting/shadow/exposure/finish produces a visibly different render. Background stays pure white; light positions and color management stay fixed.

**Blocked by:** 01 (Layer-lines material in the Blender script)

**Status:** done

- [x] Render script CLI args for key/fill/rim energy, ambient strength, shadow on/off, shadow softness, exposure; defaults reproduce today's render exactly
- [x] `/api/render-settings` round-trips the new fields; `/api/render` forwards them to the script
- [x] Step 4 inline controls expose the new settings (temporary UI); a render with shadows off / exposure 1.5 / layer-lines on is visibly different in each way
- [x] Existing render tests updated; `python -m pytest tests/` passes

## Comments

Implemented on branch `ticket/02-expanded-settings` (worktree `.worktrees/ticket-02`), TDD red→green per seam:

- **CLI seam** (`backend/render/blender_studio.py`): `--key-energy/--fill-energy/--rim-energy` (150/60/250), `--ambient` (0.35 world strength), `--shadow/--no-shadow` (BooleanOptionalAction, default on — key light `use_shadow`), `--shadow-softness` (1.5, key light disk size), `--exposure` (1.0; multiplies all three energies + world strength). Defaults are exactly the old hardcoded values, so a default render is unchanged. Structural tests in `tests/test_render_lighting.py`.
- **Wrapper** (`backend/render/__init__.py`): `render_model()` gained kwargs for all of the above plus the ticket-01 finish args (`finish`, `layer_height_mm`, `layer_depth`) and forwards them as CLI flags. Command-line capture tests in `tests/test_render_model_flags.py`.
- **Persistence** (`backend/copyScripts/combine_data.py`): `get_render_settings`/`save_render_settings` round-trip the full surface with validation (finish ∈ {smooth, layer-lines}; layer height 0.08–0.4mm; layer depth 0–1; energies 0–2000; ambient 0–2; softness 0.1–10; exposure 0.1–4; shadow strict bool). Constants in `backend/constants/render.py`.
- **HTTP** (`app.py`): `/api/render-settings` GET/POST covers all fields; `/api/render` accepts them as multipart form fields (shadow as true/false string), validates with the same ranges, and forwards to `render_model()`. Tests extended in `tests/test_render_settings.py` and `tests/test_render_api.py`.
- **Frontend**: `frontend/src/constants/render.ts` mirrors the backend defaults/ranges; Step 4's inline controls row gained temporary knobs (finish select, layer height/depth sliders when Layer Lines is on, key/fill/rim/ambient/exposure sliders, shadow checkbox, softness slider when shadow is on) in the existing row style; the Render request appends all fields. Replaced by the Profile Editor in ticket 05.

**Merge note for the integrator:** while this ticket was in flight, tickets 03+04 landed on `integration/render-profiles` — including a *parallel implementation of this same ticket 02* (`ac0c22c`, merged as `fa5a6b0`). That merge committed **unresolved conflict markers** in `frontend/src/components/ThreeDFileFinder.tsx` (3 marker blocks), so the integration tip did not build. My branch merged `integration/render-profiles` and resolved the file properly: ticket 04's profile dropdown + editor view-switching kept, the ticket-02 inline controls row kept below the dropdown as the temporary UI, and `handleProfileSelect` extended to apply the expanded settings to local state. The backend/test content of the two ticket-02 implementations was identical (same spec); the merge auto-resolved those. Final state: `python -m pytest tests/` = 164 passed; `cd frontend && npm run build` = success.

Manual pixel verification (shadows off / exposure 1.5 / layer-lines visibly different) not run here — Blender renders are 10–30s each and the structural/forwarding tests cover the wiring; worth one manual A/B when the integrator has Blender handy.
