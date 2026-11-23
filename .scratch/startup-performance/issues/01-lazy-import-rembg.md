# 01: Lazy-import rembg in imageEditing

**What to build:** The backend dev server boots in ~1.3s instead of ~3.8s. Today `backend/copyScripts/imageEditing.py` imports `from rembg import remove` at module scope, which pulls in the numba/scipy/onnxruntime chain and costs ~2.5s of every `import app` (measured via `-X importtime`; see `docs/research/startup-performance.md`). Moving that import into the `remove_background()` function body defers the cost until a background-removal request actually arrives; Python's module cache makes subsequent calls free. The only user-visible change is that the first background-removal request after a boot pays a one-time ~2.5s.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] `from rembg import remove` no longer executes at module scope in `imageEditing.py`; it is imported inside `remove_background()`.
- [ ] `remove_background()` still returns PNG bytes with the background removed, unchanged behavior for callers.
- [ ] `python -X importtime -c "import app"` shows cumulative import time dropped from ~3.3s to roughly ≤1s (rembg/pymatting/numba/onnxruntime no longer in the tree).
- [ ] Backend still starts and serves requests (`python app.py` binds :5000; a non-rembg endpoint responds).
- [ ] A background-removal request still works end-to-end (pays the one-time import cost on first call, fast after).
