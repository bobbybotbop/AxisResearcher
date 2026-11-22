# 07: Image confirmation (pHash comparison)

**What to build:** New `POST /api/compare-images` endpoint accepting `{ebay_photos: [...], site_url: string}`. Downloads eBay listing photos and site images (via the scraper from ticket 04), computes perceptual hashes using the ImageHash library, compares all pairs, and returns `{match: boolean, matched_pairs: [{ebay_index, site_index, distance}]}`. Non-blocking — the result labels the saved 3D file as "Confirmed image match" or "Unconfirmed title match" but does not prevent download. ImageHash is added as a pip dependency.

**Blocked by:** 04 (site image scrapers)

**Status:** done

- [ ] `POST /api/compare-images` accepts eBay photo URLs and a site URL
- [ ] Downloads both sets of images and computes pHashes
- [ ] Returns match boolean and matched pairs with distances
- [ ] ImageHash library is added as a dependency
- [ ] Comparison is reasonably fast (< 10 seconds for typical image sets)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
