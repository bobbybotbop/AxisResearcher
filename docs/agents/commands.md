# Commands

Run from the project root unless noted.

## Dev server

```
npm run dev              # backend (python app.py) + frontend (vite), waits for backend on :5000 first.
                         # Kills any stale python app.py process holding :5000 on startup.
                         # --kill-others-on-fail tears down both if the backend dies.
                         # If Ctrl+C prompts "Terminate batch job (Y/N)?", answer Y.
npm run dev:backend      # python app.py only (Flask, port 5000)
npm run dev:frontend     # cd frontend && npm run dev only (Vite, port 4000, proxies /api -> :5000)
```

```
npm run force-close     # kill stale backend/frontend dev processes and free ports 4000-4010 + 5000.
                         # Catches orphaned Vite servers and npm/concurrently wrappers that a
                         # port-only scan misses. TIME_WAIT sockets (PID 0) cannot be killed —
                         # if it warns, wait ~1-2 minutes and retry.
```

Frontend build/preview (run inside `frontend/`):
```
npm run build
npm run preview
```

## Backend dependencies

```
pip install -r requirements.txt
```

Config: copy `env_template.txt` to `.env` (eBay creds, business policy IDs, `openrouter_api_key`, `bedrock_api_key`).

## Token scripts

```
python testing/test_update_tokens.py verify           # show which token env vars are set
python testing/test_update_tokens.py mint-app          # mint a fresh application token, write to .env
python testing/test_update_tokens.py refresh-user       # refresh the user token
python testing/test_update_tokens.py exchange <code>    # exchange an OAuth consent code for a user token
```

## Research CLI

```
python -m backend.ebay_cli refresh                                          # refresh OAuth tokens (application + user)
python -m backend.ebay_cli collect <seller_username> [query] [limit]        # collect a seller's item IDs -> Collected-Data/<seller>/
python -m backend.ebay_cli process <seller_username> [limit] [output_file]  # fetch sales data -> processed-sales-data/
python -m backend.ebay_cli top [input_file] [top_n] [output_file]           # extract top sellers from a processed file
python -m backend.ebay_cli copy <item_id_or_url>                            # copy + AI-optimize a single listing
python -m backend.ebay_cli search <query> / seller <username> / item <item_id>
```
