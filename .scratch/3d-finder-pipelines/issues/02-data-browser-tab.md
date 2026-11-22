# 02: Data Browser tab

**What to build:** New top-level "Data Browser" tab in the sidebar (between Saved 3D Files and Logs). File-browser-style layout: left sidebar lists tables (listings, preferences, logs, prompts), main area shows paginated rows of the selected table. Click a row to expand full detail — all fields displayed, image URLs rendered as inline images (not just text). Purely visual browsing, no SQL query interface.

**Blocked by:** 01 (SQLite database foundation)

**Status:** done

- [ ] "Data Browser" tab appears in the sidebar between Saved 3D Files and Logs
- [ ] Left sidebar lists all tables; clicking selects a table
- [ ] Main area shows paginated rows with key columns visible
- [ ] Clicking a row expands full detail with all fields
- [ ] Image URLs in listing rows render as inline images
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
