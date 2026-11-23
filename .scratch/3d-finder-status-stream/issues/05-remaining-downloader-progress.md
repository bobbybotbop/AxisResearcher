# 05: Progress callbacks in the remaining four downloaders

**What to build:** Printables, MakerWorld, Cults3D, and Thangs downloads emit the same kind of live per-file progress Thingiverse got in ticket 04 — real counts where the site exposes a file list, phase-level friendly messages where it does not. The optional `progress_cb` parameter is added to each downloader with the same shape as Thingiverse's, defaulting to `None` so existing callers are unaffected. Every enabled site in the download step now streams the most detailed honest status available.

**Blocked by:** 04 (Stream Step 3 download + two-phase file delivery, Thingiverse first)

**Status:** done

- [ ] All four downloaders accept the optional `progress_cb` with the same signature/shape as Thingiverse's
- [ ] Per-file counts are emitted wherever the site API exposes a real file list; otherwise honest phase messages only (no invented numbers)
- [ ] Downloading from each of the four sites shows live status in the wizard and the file still saves correctly in both modes
- [ ] `python -m pytest tests/` passes; `cd frontend && npm run build` passes
