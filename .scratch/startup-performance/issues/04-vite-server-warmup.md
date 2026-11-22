# 04: Vite server.warmup for first paint (optional)

**What to build:** Adds `server.warmup.clientFiles` to `frontend/vite.config.ts` for the heavy entry modules (`./src/App.tsx`, `./src/components/CreateWorkflow.tsx`) so Vite pre-transforms them at server start rather than on first browser request. This shaves a few hundred ms off browser first-paint. It does not change Vite's "ready" time and is a small, optional polish win — only worth landing if first paint still feels slow after tickets 01+02. Per the Vite docs, do not over-warm (keep the list short).

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] `frontend/vite.config.ts` adds `server.warmup.clientFiles` listing the heavy entry modules.
- [ ] Vite dev server still starts and reports "ready" without errors.
- [ ] The app loads in the browser without new errors; first paint is unchanged or faster.
- [ ] `cd frontend && npm run build` (or `tsc --noEmit`) passes.
