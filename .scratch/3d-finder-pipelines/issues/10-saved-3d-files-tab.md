# 10: Saved 3D Files tab

**What to build:** New top-level "Saved 3D Files" tab in the sidebar (between History and Data Browser). Searchable, paginated card list matching the History tab layout (compact and detailed view modes). Each card shows: title, source site badge, match label badge ("Confirmed image match" / "Unconfirmed title match"), pipeline badge ("Image Search" / "Title Search"), timestamp, image gallery (from 3D site images stored locally). Click a card to open a detail modal showing all metadata, full image gallery, a download button (to re-download the 3D file), and a delete button.

**Blocked by:** 09 (Saved 3D Files table + auto-save)

**Status:** done

- [ ] "Saved 3D Files" tab appears in sidebar between History and Data Browser
- [ ] Card list matches History tab layout (compact + detailed view modes)
- [ ] Each card shows title, badges (site, match label, pipeline), timestamp, image gallery
- [ ] Click opens detail modal with all metadata, image gallery, download and delete buttons
- [ ] Search/filter works on title and source site
- [ ] Pagination works
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
