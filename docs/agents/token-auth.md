# eBay OAuth Token Architecture

Two independent token types with distinct lifecycles.

## Token types

**Application token** (client credentials grant) — Browse API / Commerce Taxonomy (read-only).
- Minted via `mint_application_token()` in `backend/refreshToken.py`
- Lifetime: 2 hours. Auto-refreshed on 401 in CLI Browse API calls.

**User token** (authorization code grant) — Sell Inventory API / Trading API (writes).
- Lifetime: 2 hours. Refreshed from the long-lived `refresh_token`.
- Refresh: `refresh_user_token()` in `backend/refreshToken.py` POSTs to `https://api.ebay.com/identity/v1/oauth2/token` with `grant_type=refresh_token`.

**Refresh token** — the long-lived credential (~18 months) stored in `.env`.
- Obtained only via the full OAuth consent flow (user logs in, approves scopes, code exchanged).
- **Revoked immediately** if the user changes their eBay password or revokes app consent.
- When revoked, `refresh-user` may appear to succeed (200 response) but the resulting user_token will fail with 401 on actual API calls.

## Token commands

| Task | Command |
|------|---------|
| Refresh user + app tokens (normal) | `python -m backend.ebay_cli refresh` |
| Verify .env token state | `python testing/test_update_tokens.py verify` |
| Full re-consent (when refresh token is revoked) | `python -m backend.refreshToken open-consent` → approve → `python testing/test_update_tokens.py exchange <code>` |
| Mint application token only | `python testing/test_update_tokens.py mint-app` |

## Token flow in code

- `backend/refreshToken.py` — all OAuth endpoint calls (mint, consent URL, exchange, refresh). Writes results to `.env` via `update_env()`.
- `backend/helper_functions.py` — `refreshToken()` is the CLI's single "refresh everything" entry point; calls `refresh_user_and_app_token()`.
- `backend/ebay_cli.py` — on 401 from Browse API calls, auto-retries with `_refresh_application_token_and_retry()`.
