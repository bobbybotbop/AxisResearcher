# Constants discipline

All magic strings, magic numbers, hardcoded lists, and configuration values must live in constants files. Never inline them at call sites.

- **Backend**: `backend/constants/<domain>.py`
- **Frontend**: `frontend/src/constants/<domain>.ts`

When adding a new value, find the most relevant existing constants file or create a new domain file.

## Backend domains

- `ebay` — API URLs, OAuth config
- `models` — AI model IDs, prompt filenames
- `listing` — title rules, SKU prefixes, image category maps
- `serp` — whitelisted/blacklisted sites
- `paths` — filesystem paths and log limits

## Frontend domains

- `models` — model option arrays, provider labels
- `routes` — tab paths and `TabName` type
- `logs` — event labels, filter chips
- `chatContextModes` — chat context config
- `placeholder` — test-user placeholder image data URLs
- `cooldown` — auto-operation cooldown default and stock-snapshot localStorage keys

## What is NOT moved to constants

- Values loaded from `.env` or `listingPreferences.json` at runtime (these are config)
- The `ImageType` enum (it is a type, not a value)
- One-off inline LLM prompt strings
