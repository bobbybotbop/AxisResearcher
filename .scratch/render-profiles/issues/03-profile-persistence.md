# 03: Render Profile persistence + API

**What to build:** Render Profiles (GLOSSARY.md) persist server-side: a `render_profiles` list (each: name + full settings snapshot) and the active profile name in `listingPreferences.json`, with `get/save_render_profiles` helpers in `combine_data.py` following the existing `get/save_*` settings pattern, and a `/api/render-profiles` route supporting list, create, update, delete. "Current Settings" is not a stored profile — it is the implicit default entry representing the flat settings; deleting the active profile falls back to it. Verified via API calls only; no UI in this ticket.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `GET /api/render-profiles` returns the saved list; `POST` creates; `PUT`/POST-update overwrites by name; `DELETE` removes by name
- [x] Active profile name persists and survives a server restart; deleting the active profile resets it to "Current Settings"
- [x] Duplicate profile names rejected with a clear error
- [x] Tests cover create/list/update/delete round-trip; `python -m pytest tests/` passes

## Comments

Implemented on branch `ticket/03-profile-persistence` (worktree `.worktrees/ticket-03`), merged with `integration/render-profiles` tip (no conflicts; ticket 01's layer-lines tests came in and pass).

**Storage shape** (in `listingPreferences.json`):
- `render_profiles`: flat dict `{name: settings_dict}` — a dict rather than a list, so lookup/overwrite by name is O(1) and duplicates are structurally impossible at the storage layer (the API still checks and returns a clear 400). Settings values are flat dicts; unknown keys pass through untouched, so ticket 02 can add fields (surface finish, lighting, shot mode, rig) without a schema migration.
- `active_render_profile`: profile name or `null` (= "Current Settings", the implicit default — never a stored profile).

**Helpers in `backend/copyScripts/combine_data.py`** (mirroring `get/save_render_settings`): `get_render_profiles()`, `save_render_profile(name, settings)`, `delete_render_profile(name)`, `get_active_render_profile()`, `set_active_render_profile(name)`. Known fields (color/roughness/resolution/fov) are validated with the exact same rules as `save_render_settings` (validators shared via small private helpers). Reserved names rejected: "Current Settings" (any case) and "active" (would shadow the `/active` route).

**Routes in `app.py`**:
- `GET /api/render-profiles` → `{"profiles": {...}, "active": name|null}`
- `POST /api/render-profiles` `{"name", "settings"}` → 201; duplicate name → 400 "already exists"
- `POST`/`PUT /api/render-profiles/<name>` `{"settings"}` → overwrite; unknown name → 404
- `DELETE /api/render-profiles/<name>` → 200/404; deleting the active profile resets `active` to null
- `POST /api/render-profiles/active` `{"name": str|null}` → set active; unknown name → 400

**Tests:** 31 new tests in `tests/test_render_profiles.py` covering both seams (persistence helpers + HTTP routes), including restart-survival via a fresh test client, extra-key passthrough, and all rejection paths. Full suite: **129 passed** (`python -m pytest tests/`).

**Note for merger:** the worktree venv was missing `trimesh`/`gmsh` (documented project deps from the Render Mesh glossary entry); the mesh-normalization tests error without them. I ran `pip install trimesh gmsh` in the worktree venv to get the full suite green — other worktrees/CI may need the same. No code change was needed for that.
