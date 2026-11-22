# 01: SQLite database foundation + migration

**What to build:** Create `axis.db` in the project root using Python stdlib `sqlite3`. Tables: `listings` (flattened key columns + `raw_json` TEXT), `preferences` (key-value with JSON-serialized values), `logs` (id, timestamp, event, status, details, auto-trim to 1000), `prompts` (name, content, updated_at). One-time auto-migration on first run: if `axis.db` doesn't exist, read all existing data from `listingPreferences.json`, `Generated_Listings/*.json`, `logs.ndjson`, and `prompts/**/*.txt` into the database. All existing endpoints switch from file-based to SQLite reads/writes. The app works identically after migration — no visible UI change. Old JSON files are kept as backup (not deleted).

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `axis.db` is created in the project root with the four tables
- [x] Auto-migration imports all existing data from JSON files on first run
- [x] All existing API endpoints read/write SQLite instead of JSON files
- [x] The app behaves identically — no regressions in any existing functionality
- [x] Old JSON files are preserved (not deleted)
- [x] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
