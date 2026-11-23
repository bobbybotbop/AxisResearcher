# 03: Background-warm rembg after server bind

**What to build:** After ticket 01, the first background-removal request after a boot pays a one-time ~2.5s rembg import. This ticket erases that penalty: once the Flask server starts listening, a daemon thread triggers the rembg import in the background so the module is already in `sys.modules` by the time any request needs it. Boot latency stays at ~1.3s (the import happens off the critical path), and even the first background-removal request is fast.

**Blocked by:** 01 (Lazy-import rembg) — the warm only exists to erase the first-request penalty that the lazy import introduces.

**Status:** resolved

- [ ] After the server binds :5000, a background daemon thread imports rembg (or calls a warm path that triggers the lazy import) without blocking boot.
- [ ] Backend spawn-to-listening time is unchanged from ticket 01 (~1.3s); the warm does not delay the bind.
- [ ] The first background-removal request after boot no longer pays the ~2.5s import (it completes in normal request time).
- [ ] The warm is failure-safe: if rembg fails to import in the background, the server keeps running and the first real request surfaces the error as before.
- [ ] Backend still starts and serves requests normally.
