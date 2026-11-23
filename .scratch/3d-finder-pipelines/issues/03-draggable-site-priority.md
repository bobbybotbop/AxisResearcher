# 03: Draggable site priority in Settings

**What to build:** The 3D File Sites section in Settings becomes a draggable ordered list using `@hello-pangea/dnd` (the project's existing DnD library). The drag order represents site priority and is stored in localStorage. Each site shows two status badges: "Download: Operational/Down/Not tested" and "Images: Operational/Down/Not tested" (image badge shows "Not tested" for now — probes come in ticket 04). The priority order is sent to the backend with search requests and used to rank results in both pipelines.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] 3D File Sites in Settings are rendered as a draggable ordered list
- [ ] Drag-and-drop reorders sites; order persists in localStorage
- [ ] Each site shows two status badges (download + image scraping)
- [ ] Priority order is sent to backend with search requests
- [ ] Backend uses priority order to rank whitelisted results
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
