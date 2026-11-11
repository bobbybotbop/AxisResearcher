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

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
