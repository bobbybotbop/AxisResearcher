# 02: Migrate Settings + Saved 3D Files to the store

**What to build:** Settings (token test, AI model test) and Saved 3D Files (load, delete) report their waiting state through the Status Store instead of local `is*` booleans. Saved 3D Files shows skeleton cards while loading. Token/model test keep a button spinner (single request/response, no count). Proves the store API on low-stakes ground before the Create workflow migrates.

**Blocked by:** 01 (Status Store + Task/Pipeline model)

**Status:** done

- [ ] Saved 3D Files shows skeleton cards while loading
- [ ] Saved 3D Files delete reports through the store (task + toast)
- [ ] Settings token test and model test report through the store (button spinner + toast)
- [ ] No local `is*` booleans remain for these features' waiting state
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
