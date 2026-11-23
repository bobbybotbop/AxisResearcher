# 02: Start Vite in parallel with the backend

**What to build:** `npm run dev` starts the Vite dev server immediately instead of serializing it behind the backend via `wait-on`. Today the root `dev` script runs `wait-on tcp:127.0.0.1:5000 && cd frontend && npm run dev`, so Vite's ~630ms start only begins after the backend's full boot. Vite's `/api` proxy tolerates a down backend (it only errors when a request actually arrives), so both servers can start in parallel and total boot becomes max(backend, frontend) instead of the sum. The one hazard: the launch-time auto-token-refresh in `App.tsx` sets `hasAutoRefreshed` before the request and never retries on failure, so dropping the wait would cause a skipped refresh + spurious error toast on cold boot. This ticket makes that refresh retry until the backend is up.

**Blocked by:** None (can start immediately, in parallel with 01)

**Status:** resolved

- [ ] Root `dev` script no longer gates the frontend start on `wait-on tcp:127.0.0.1:5000`; both servers start in parallel.
- [ ] The launch auto-token-refresh in `App.tsx` retries on failure (with backoff) until it succeeds, and only sets `hasAutoRefreshed` on success — so a not-yet-up backend no longer causes a skipped refresh.
- [ ] No spurious "Failed to refresh tokens" error toast on a normal cold boot once the backend comes up.
- [ ] `npm run dev` brings up both servers; the frontend is reachable on :4000 and proxies /api to :5000 once the backend is listening.
- [ ] `cd frontend && npm run build` (or `tsc --noEmit`) passes.
