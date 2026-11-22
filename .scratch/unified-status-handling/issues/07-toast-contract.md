# 07: Toast migration (contract): delete ToastContainer, migrate remaining callers

**What to build:** `ToastContainer` is deleted. Every remaining `addToast` call site migrates to the Status Store's toast API. One toast system remains (bottom-right, success auto-dismiss, error persists). This is the contract half of the expand–contract: it can only land once every feature that used `addToast` has migrated off it.

**Blocked by:** 02 (Settings + Saved 3D Files), 03 (Create), 04 (History/Upload), 05 (Testing pipelines), 06 (Data Browser + Logs)

**Status:** done

- [ ] `ToastContainer` is deleted
- [ ] No `addToast` call sites remain; all use the store's toast API
- [ ] Exactly one toast system renders (bottom-right)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
