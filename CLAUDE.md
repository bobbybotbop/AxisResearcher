# CLAUDE.md

AxisResearcher is an eBay research/listing tool: Flask backend (`app.py` + `backend/`) + React/Vite frontend (`frontend/`). There is also a standalone research CLI (`python -m backend.ebay_cli`).

## Commands

See `docs/agents/commands.md`.

## OAuth token architecture

See `docs/agents/token-auth.md`.

## Backend and frontend architecture

See `docs/agents/architecture.md`.

## Constants discipline

See `docs/agents/constants.md`.

## Progress feedback

See `docs/agents/progress-feedback.md`.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), recorded as a `Status:` line in each issue file. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Worktrees

`/implement-spec` runs each spec in an orchestrator worktree under `.worktrees/` with its own dev stack on dedicated ports; `npm run dev` auto-bootstraps any worktree, and `./wt` switches between them. Ticket worktrees are tests-only. See `docs/agents/worktrees.md`.
