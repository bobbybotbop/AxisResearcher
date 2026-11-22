# 04: Site image scrapers (per-site modules + probes)

**What to build:** New `POST /api/scrape-site-images` endpoint accepting a URL and returning main model gallery image URLs. Per-site image scraper functions added to each downloader module, using the established transport: Thingiverse via v2 API `things/{id}/complete` → `images[].url`; Printables via GraphQL `images[].filePath` → `media.printables.com/{filePath}`; Thangs via `__NEXT_DATA__` → `attachments[].imageUrl`; MakerWorld via SSR `div.swiper-slide > img.swiper-lazy` src (strip resize params) or design API `pictures[]`; Cults3D via lightbox `div.slides__slide img` `data-src` → `fbi.cults3d.com` originals. Each scraper has its own `probe_images()` function with a hardcoded model ID. New `GET /api/test-3d-site-images` endpoint probes all scrapers concurrently. Yeggi excluded (no scraper, always returns empty).

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `POST /api/scrape-site-images` returns main model image URLs for a given 3D file site URL
- [x] Each site (Thingiverse, Printables, Thangs, MakerWorld, Cults3D) has a working image scraper
- [x] Each scraper uses the site's established transport (API/DOM as appropriate)
- [x] `GET /api/test-3d-site-images` probes all scrapers and returns per-site status
- [x] Yeggi returns empty/error gracefully
- [x] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
