# 04: Profile dropdown in Step 4

**What to build:** Step 4's inline settings row is replaced by a Render Profile dropdown: saved profiles plus the always-present "Current Settings" default, an Edit button per row, a delete button (with confirm) per saved profile, and a "Create new profile" entry. Selecting a profile copies its values into Current Settings (the flat settings), so the render path is unchanged; the selection is sticky (persisted as the active profile). In this ticket the Edit / Create actions open a placeholder (the editor arrives in ticket 05) — wire the navigation state so 05 only fills in the editor view.

**Blocked by:** 03 (Render Profile persistence + API)

**Status:** done

- [x] Dropdown lists saved profiles + "Current Settings"; selection persists across reload
- [x] Selecting a profile copies its values into the flat settings (verified: subsequent `/api/render-settings` GET reflects them)
- [x] Delete removes a profile after confirm; deleting the active profile falls back to "Current Settings"
- [x] Edit / Create-new navigate to an editor placeholder state within the Step 4 panel
- [x] `cd frontend && npm run build` passes

## Comments

- Implemented on branch `ticket/04-profile-dropdown` (commit 9a0456a), merged `integration/render-profiles` — already up to date, no conflicts.
- New component `frontend/src/components/RenderProfileDropdown.tsx`: lists "Current Settings" (active=null) first, then saved profiles sorted alphabetically; per-row Edit; delete via two-step inline confirm ("Delete X?" Yes/No); "+ Create new profile" entry at the bottom. Closes on outside click / Escape.
- Selection flow: on select the component POSTs `/api/render-profiles/active` (sticky) and calls `onSelect`; `ThreeDFileFinder.handleProfileSelect` POSTs the profile's settings object **verbatim** to `/api/render-settings` (no field enumeration — ticket 02's new fields flow through untouched) and updates local color/roughness/resolution/fov state so the preview/Render button reflect the selection immediately. Selecting "Current Settings" POSTs active=null and leaves the flat settings alone.
- Editor navigation: `step4View: 'dropdown' | 'editor'` + `editingProfile: string | null | 'create'` in `ThreeDFileFinder.tsx`. The dropdown's `onEdit(mode, name)` maps: `"edit"` → name, `"edit-current"` → null (Current Settings), `"create"` → `"create"`. The placeholder block in Step 4 shows which mode was opened and a "← Back to profiles" button; ticket 05 replaces only that block.
- The inline color/glossiness/resolution controls were removed; the FOV slider (below the preview) still uses `persistRenderSettings` and is unchanged. Render button + preview read the same flat-settings state as before.
- Verification: no frontend test framework exists in this project (no vitest/jest, no test script), so verification was `npm run build` (passes), `npm run type-check` (passes), plus an end-to-end API smoke test with Flask's test client against the worktree backend: create profile → set active → POST its settings to `/api/render-settings` → GET reflects them → delete active profile → active falls back to null. All passed; `listingPreferences.json` side effects were reverted.
- Note for ticket 05: the placeholder is the `step4View === "editor"` block in `ThreeDFileFinder.tsx`; `editingProfile` tells the editor what it opened for. `RenderProfileDropdown` holds its own profiles list — if the editor creates/renames profiles, the dropdown re-reads them on next mount (or lift the fetch up if stale lists become a problem).
