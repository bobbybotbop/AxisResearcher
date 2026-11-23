# 05: Adopt Bun for frontend installs + script runner (optional)

**What to build:** Adopts Bun in `frontend/` as the package installer and script runner, per the prior research in `docs/research/bun-migration.md` (which cleared it as safe and recommended). Running `bun install` in `frontend/` generates `bun.lock` auto-migrated from the existing `package-lock.json` (lockfileVersion 3) while preserving the original, so the change is reversible. The dev invocation switches to `bun run dev`, cutting most of the ~600ms npm script-runner overhead on Windows and making future installs much faster. Vite itself still runs on Node (Bun respects its `#!/usr/bin/env node` shebang), so there is no runtime-compat risk. Scope is deliberately frontend-only: the root orchestration script stays on npm because its cmd-style paths (`.venv\Scripts\python`, `&&` chaining) behave differently under Bun Shell (flagged as the biggest friction point in the prior research).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] `bun install` run in `frontend/`; `bun.lock` generated and committed; original `package-lock.json` preserved (not deleted) so the change is reversible.
- [ ] Frontend dev/build/type-check invoked via `bun run` work: `bun run dev` serves :4000, `bun run build` builds, `bun run type-check` passes.
- [ ] Vite still runs under Node (not `bun --bun`); the app loads and proxies /api normally.
- [ ] The `canvas` optional dep's install script stays skipped (not added to `trustedDependencies`) — it is unneeded for a browser fabric app.
- [ ] Root `dev` orchestration still works (root stays on npm; only the frontend invocation changes). If ticket 02 also lands, the root script's frontend call uses `bun run dev` while the root itself stays on npm.
- [ ] README/docs note the Bun requirement for frontend dev, or a fallback documented for contributors without Bun.
