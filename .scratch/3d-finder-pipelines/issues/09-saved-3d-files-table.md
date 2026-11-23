# 09: Saved 3D Files table + auto-save

**What to build:** New `saved_3d_files` table in SQLite with columns: id, ebay_listing_url, ebay_listing_title, source_site, source_url, match_label, pipeline, file_path, images_dir, created_at. Every successful download from either pipeline auto-saves a record. Site images are downloaded and stored locally in a per-entry directory. eBay photos are not stored (only the listing URL). The match label comes from the image confirmation (ticket 07) for Title Search, or is always "Confirmed image match" for Image Search. New endpoints: `GET /api/saved-3d-files` (list, paginated), `GET /api/saved-3d-files/<id>` (detail), `DELETE /api/saved-3d-files/<id>` (delete).

**Blocked by:** 01 (SQLite database foundation), 08 (Testing tab restructure)

**Status:** done

- [ ] `saved_3d_files` table exists in SQLite with all specified columns
- [ ] Every successful download from either pipeline auto-saves a record
- [ ] Site images are downloaded and stored locally per entry
- [ ] eBay photos are not stored (only the listing URL)
- [ ] Match label is set correctly per pipeline
- [ ] `GET /api/saved-3d-files` returns paginated list
- [ ] `GET /api/saved-3d-files/<id>` returns full detail
- [ ] `DELETE /api/saved-3d-files/<id>` removes entry and associated files
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
