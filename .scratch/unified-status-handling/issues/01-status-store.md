# 01: Status Store + Task/Pipeline model + toast unification (expand)

**What to build:** The Status Store exists as the single owner of all waiting-state UI: a Task/Pipeline model (Task = id, name, status pending/running/success/error, optional current/total progress, optional error; Pipeline = named ordered sequence of Tasks with a current index) and a handle API (`startTask(name, {total})` returns `{progress, succeed, fail}`; `startPipeline(name, steps)`). `StartupToasts` becomes the store's toast module (bottom-right, single system; success auto-dismisses, error persists). `ToastContainer` still exists alongside — nothing breaks, no feature migrates yet. The store is demoable via a temporary harness. Scope is strictly waiting-state UI: the store never touches feature inputs or outputs.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] Status Store exists with Task/Pipeline model and `startTask`/`startPipeline` handle API
- [ ] `StartupToasts` is the store's toast module; toasts render bottom-right as one system
- [ ] `ToastContainer` and all existing callers still work unchanged (expand, not contract)
- [ ] Store is demoable via a temporary harness (a task and a pipeline can be started, progressed, succeeded, failed)
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
