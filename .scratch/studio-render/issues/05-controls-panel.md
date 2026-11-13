# 05: Controls panel + persisted Render Settings

**What to build:** The Studio Render panel gains a controls panel with a color picker (default near-black #1a1a1a), a glossiness slider (maps to Principled roughness, default ~0.3), and a square-resolution dropdown (512 / 1024 / 2048, default 1024). These plus the FOV slider value persist as Render Settings in `listingPreferences.json` through a `/api/render-settings` GET/POST route, mirroring the existing `get/save_*_settings` pattern, and reload when the panel reopens. Each render applies the chosen color, glossiness, and resolution to the Blender scene. Lighting, exposure, and background remain fixed and unexposed.

**Blocked by:** 02 (Tracer bullet — fixed-angle render, end to end).

**Status:** ready-for-agent

- [ ] Color picker, glossiness slider, and resolution dropdown exist and affect the render output visibly (color and glossiness change; resolution changes image dimensions)
- [ ] Settings persist across page reloads via `listingPreferences.json` and the `/api/render-settings` route
- [ ] Camera angle remains ephemeral (not persisted)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
