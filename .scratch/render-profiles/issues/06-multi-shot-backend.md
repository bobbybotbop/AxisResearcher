# 06: Multi-shot Camera Rig in the backend

**What to build:** Shot Mode and Camera Rig (GLOSSARY.md) reach the backend: the settings schema and profiles carry shot mode (`single`/`multi`) and a rig (ordered list of cameras, each azimuth + elevation; roll fixed 0). `/api/render` accepts a rig and fans out N sequential Render Jobs (sequential, not parallel — Cycles CPU saturates the machine), returning N images. The 10 named angle presets (front, top, left, right, bottom, back, front-right, back-left, front-top-left, back-bottom-right) are defined once in shared constants with their azimuth/elevation values. Verified via API: POST a 3-camera rig, receive 3 correctly-angled renders. No UI in this ticket.

**Blocked by:** 02 (Expanded settings end-to-end)

**Status:** done

- [x] Settings/profile schema carries shot mode + rig; `/api/render-settings` and `/api/render-profiles` round-trip them
- [x] `/api/render` with a rig produces one image per camera, sequential jobs, correct azimuth/elevation per image
- [x] 10 angle presets defined in shared constants (backend + frontend mirror, like the existing render constants)
- [x] Single-shot behavior unchanged when shot mode is `single`
- [x] Tests cover multi-shot fan-out; `python -m pytest tests/` passes

## Comments

Implemented in commit c5a6f9b + merge d11e261; 199 tests passing at that point.

- Presets use ±89° for top/bottom rather than ±90° — this avoids the elevation ±90° singularity where the camera looks straight down/up the Y axis and azimuth is meaningless.
- Azimuth range is −360..360 (negative values orbit counterclockwise); presets already used negative azimuths (e.g. left = −90), and GLOSSARY.md's Camera Rig entry has been updated to match the implementation.
- The agent's connection failed during wrap-up, so this bookkeeping (ticking checkboxes + comments) was completed post-hoc in the review-fixes pass.
