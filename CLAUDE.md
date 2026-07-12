# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AxisResearcher is an eBay research/listing tool with two parts:
- A Flask backend (`app.py` + `backend/`) that talks to the eBay Browse/Trading APIs and to AI providers (OpenRouter, AWS Bedrock) to research listings, generate optimized copy/images, and publish listings.
- A React (Vite) frontend (`frontend/`) that drives the "copy a listing → generate photos/text → create → upload" workflow.

There is also a standalone CLI (`backend/ebay_cli.py`, invoked via `python -m backend.ebay_cli`) for bulk seller research (collect/process/top) that is independent of the Flask app.

## Commands

Run from the project root unless noted.

```
npm run dev              # backend (python app.py) + frontend (vite), waits for backend on :5000 first
npm run dev:backend      # python app.py only (Flask, port 5000)
npm run dev:frontend     # cd frontend && npm run dev only (Vite, port 4000, proxies /api -> :5000)
```

Frontend build/preview (run inside `frontend/`):
```
npm run build
npm run preview
```

There is no configured lint or automated test suite (no ESLint config, no pytest/jest/vitest). `testing/test_update_tokens.py` is a manual CLI script for exercising the OAuth token flow, not an automated test:
```
python testing/test_update_tokens.py verify          # show which token env vars are set
python testing/test_update_tokens.py mint-app         # mint a fresh application token, write to .env
python testing/test_update_tokens.py refresh-user      # refresh the user token
python testing/test_update_tokens.py exchange <code>   # exchange an OAuth consent code for a user token
```

Research CLI (`python -m backend.ebay_cli`):
```
python -m backend.ebay_cli refresh                                  # refresh OAuth tokens (application + user)
python -m backend.ebay_cli collect <seller_username> [query] [limit]        # collect a seller's item IDs -> Collected-Data/<seller>/
python -m backend.ebay_cli process <seller_username> [limit] [output_file]  # fetch sales data for collected items -> processed-sales-data/
python -m backend.ebay_cli top [input_file] [top_n] [output_file]           # extract top sellers from a processed file
python -m backend.ebay_cli copy <item_id_or_url>                            # copy + AI-optimize a single listing (CLI path, not the frontend flow)
python -m backend.ebay_cli search <query> / seller <username> / item <item_id>
```

Backend deps: `pip install -r requirements.txt` (Flask, flask-cors, requests, python-dotenv, rembg[cpu], boto3).
Config: copy `env_template.txt` to `.env` (eBay creds, business policy IDs, `openrouter_api_key`, `bedrock_api_key`).

## eBay OAuth Token Architecture

The project uses two independent token types with distinct lifecycles:

**Application token** (client credentials grant) — used for Browse API / Commerce Taxonomy (read-only).
- Minted via `mint_application_token()` in `backend/refreshToken.py`
- Lifetime: 2 hours. Auto-refreshed on 401 in CLI Browse API calls.

**User token** (authorization code grant) — used for Sell Inventory API / Trading API (writes).
- Lifetime: 2 hours. Refreshed from the long-lived `refresh_token`.
- Refresh: `refresh_user_token()` in `backend/refreshToken.py` POSTs to `https://api.ebay.com/identity/v1/oauth2/token` with `grant_type=refresh_token`.

**Refresh token** — the long-lived credential (~18 months) stored in `.env`.
- Obtained only via the full OAuth consent flow (user logs in, approves scopes, code is exchanged).
- **Revoked immediately** if the user changes their eBay password or revokes app consent.
- When revoked, `refresh-user` may appear to succeed (200 response) but the resulting user_token will fail with 401 on actual API calls.

### Token commands

| Task | Command |
|------|---------|
| Refresh user + app tokens (normal) | `python -m backend.ebay_cli refresh` |
| Verify .env token state | `python testing/test_update_tokens.py verify` |
| Full re-consent (when refresh token is revoked) | `python -m backend.refreshToken open-consent` → approve → `python testing/test_update_tokens.py exchange <code>` |
| Mint application token only | `python testing/test_update_tokens.py mint-app` |

### Token flow in code

- `backend/refreshToken.py` — all OAuth endpoint calls (mint, consent URL, exchange, refresh). Writes results to `.env` via `update_env()`.
- `backend/helper_functions.py` — `refreshToken()` is the CLI's single "refresh everything" entry point; calls `refresh_user_and_app_token()`.
- `backend/ebay_cli.py` — on 401 from Browse API calls, auto-retries with `_refresh_application_token_and_retry()`.

## Backend architecture

- **`app.py`** is the whole Flask API surface (all `/api/*` routes live here — there's no blueprint split). It:
  - Uses NDJSON streaming (`progress_event`/`result_event`/`error_event` + `streaming_response`) for multi-step operations like `/api/create-listing` and `/api/upload-listing`, so the frontend can render step-by-step progress instead of waiting on one big response.
  - Tracks async image-generation jobs in an in-memory dict (`image_generation_tasks`, guarded by `image_generation_lock`) polled via `/api/generate-images-status/<task_id>`. This state is process-local — it does not survive a backend restart.
- **`backend/ebay_cli.py`** holds eBay OAuth/token logic, Browse/Trading API calls, and the CLI entrypoints used by `python -m backend.ebay_cli`. `backend/copyScripts/*` is imported from here and from `app.py`.
- **`backend/copyScripts/`** — the listing pipeline, roughly in call order:
  - `CopyListingMain.py` — fetches a listing by ID/URL, allocates the next SKU, categorizes source photos.
  - `create_image.py` — AI image generation (OpenRouter) and image categorization. Photos are classified into `professional_image` / `real_world_image` / `bad_image` / `edited_image` per the rules in `prompts/categorizeImage.txt`; generation prompts come from `prompts/generateImageFromProfessional`, `generateImageFromWorld.txt`, `experimental.txt` selected via the `ImageType` enum (`PROFESSIONAL`, `REAL_WORLD`, `EXPERIMENTAL`).
  - `create_text.py` — generates optimized title/description via `call_text_llm` (in `ebay_cli.py`), using the `prompts/generateTextPrompt.txt` template.
  - `combine_data.py` — owns the SKU counter (`listingPreferences.json`) and all reads/writes of draft listing JSON under `Generated_Listings/<SKU>.json`. This is the local "draft" store that exists between fetching a source listing and actually uploading to eBay.
  - `upload_to_ebay.py` — publishes a draft (`Generated_Listings/*.json`) as a real eBay inventory item + offer.
  - `imageEditing.py` — background removal (`rembg`) and canvas compositing.
- **`backend/text_models.py`** is the single source of truth for which text LLMs the frontend may offer, gated by which provider key is actually set in `.env` (`openrouter_api_key` → OpenRouter models, `bedrock_api_key` → Bedrock models). Bedrock calls go through boto3's `bedrock-runtime` `converse` API; `bedrock_api_key` is mirrored into `AWS_BEARER_TOKEN_BEDROCK` at import time (`_sync_bedrock_bearer_token`) since that's what boto3 reads. When adding a new text model, add it to `OPENROUTER_TEXT_MODELS`/`BEDROCK_TEXT_MODELS` here rather than hardcoding it elsewhere.
- Prompts are loaded from disk (`prompts/*.txt`) at call time, not inlined in Python — edit the `.txt` file, not the calling code, to change model behavior.

### On-disk data (all gitignored)

- `Collected-Data/<seller>/` — raw seller item-ID dumps and `processed-sales-data/` sales exports, produced by the `collect`/`process` CLI commands.
- `Generated_Listings/<SKU>.json` — draft listings for the web app's copy/create/upload flow (SKU counter lives in `listingPreferences.json`).
- `generated-images/` — AI-generated image files written by `create_image.py`.

## Frontend architecture

- `frontend/src/App.jsx` is a large single component that owns nearly all app state via parallel `useState` hooks (there's no global store/reducer). Tabs (`create`, `upload` a.k.a. History, `test-workflow`, `testing`, `settings`) are client-side routes via `react-router-dom`, mapped in `tabPaths`; they render conditionally inside one component rather than as separate route components.
- `fetchWithProgress()` (top of `App.jsx`) is the shared client for the backend's NDJSON streaming endpoints — it reads the response body line by line and calls `onProgress` for `"progress"` events, resolving with the `"result"` event's payload (or throwing on an `"error"` event).
- **Test Workflow tab**: a fully mocked, offline clone of the Create Listing workflow. It uses `mockData.js` (`MOCK_DATA`) and `setTimeout`-simulated progress instead of any network call, so the UI/UX of the create flow can be built and demoed without live eBay/OpenRouter/Bedrock credentials. Its state is namespaced with a `test`/`Test` prefix (e.g. `testHandleConfirmCategories`, `testListingLinkSubmitted`), initialized from `testWorkflowState.js`'s `createTestWorkflowState()`. **When changing the real Create workflow's handlers/state in `App.jsx` or `CreateWorkflow.jsx`, mirror the change in the corresponding `test*` handler** or the mock tab will silently drift out of sync with real behavior.
- Styling uses Tailwind v4 with semantic CSS variable tokens (`bg-surface-app`, `bg-surface-panel`, `text-text-primary`, `border-border-default`, etc.) defined in `frontend/src/styles/App.css` and toggled via `data-theme="light"|"dark"` on the root element — see `frontend/src/styles/STYLING.md` for the full token list and usage rules. Prefer these tokens over raw colors so components don't need their own dark-mode branching.
- `docs/UI_VOCABULARY.md` is the source of truth for informal-name → component mappings (e.g. "the bottom bar" → `listing-bar-post-link` → `MessageBarInput` in `CreateWorkflow.jsx`). Check it before guessing which component a UI description refers to; it also lists the exact state flags (`listingLinkSubmitted`, `testListingLinkSubmitted`) that drive each layout.
- Vite dev server runs on port 4000 and proxies `/api/*` to the Flask backend on `http://localhost:5000` (`frontend/vite.config.js`).
