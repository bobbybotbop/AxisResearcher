# Architecture — non-obvious rules

Non-obvious constraints and patterns. Read the code for what individual files do; this covers things you cannot infer from reading.

## Backend

**NDJSON streaming**: `app.py` uses `progress_event`/`result_event`/`error_event` + `streaming_response` for multi-step operations like `/api/create-listing` and `/api/upload-listing`. The frontend reads line-by-line via `fetchWithProgress()`.

**Image generation state**: `image_generation_tasks` in `app.py` is an in-memory dict guarded by `image_generation_lock`, polled via `/api/generate-images-status/<task_id>`. Process-local — does not survive a backend restart.

**Text model registry**: `backend/text_models.py` is the single source of truth for which LLMs the frontend may offer, gated by which provider key is set in `.env`. When adding a new text model, add it to `OPENROUTER_TEXT_MODELS`/`BEDROCK_TEXT_MODELS` there — don't hardcode it elsewhere.

**Prompts are on disk**: Prompts live in `prompts/*.txt` and are loaded at call time. Edit the `.txt` file to change model behavior; don't inline strings in Python.

**On-disk data** (all gitignored):
- `Collected-Data/<seller>/` — seller item-ID dumps from the `collect` CLI command
- `Generated_Listings/<SKU>.json` — draft listings (SKU counter in `listingPreferences.json`)
- `generated-images/` — AI-generated image files

## Frontend

**Single-component state**: `App.tsx` owns nearly all app state via parallel `useState` hooks. There is no global store or reducer. Tabs are client-side routes mapped in `tabPaths`.

**NDJSON client**: `fetchWithProgress()` (top of `App.tsx`) is the shared client for streaming endpoints. Calls `onProgress` for `"progress"` events and resolves with the `"result"` payload (throws on `"error"`).

**Test Workflow mirror rule**: The Test Workflow tab is a fully offline clone of the Create Listing workflow using `mockData.js` and `setTimeout`-simulated progress. **When changing a Create workflow handler or state in `App.tsx`/`CreateWorkflow.tsx`, mirror the change in the corresponding `test*` handler.** The `test`/`Test` prefix namespaces mock state. Failing to mirror causes silent drift.

**Logs tab event types**: `draft_created`, `draft_completed`, `upload`, `restock` (with `source: "manual"|"auto"`), `import`.

**Styling**: Use Tailwind v4 semantic CSS variable tokens (`bg-surface-app`, `bg-surface-panel`, `text-text-primary`, `border-border-default`, etc.) defined in `frontend/src/styles/App.css`. Do not use raw colors — tokens toggle automatically in dark mode. See `frontend/src/styles/STYLING.md` for the full token list.

**UI vocabulary**: See `docs/UI_VOCABULARY.md` for informal-name → component mappings before guessing which component a UI description refers to.

## Image prompt workflow

Two cases depending on whether images have already been generated:

**Pre-generation** (images not yet generated): prompt stored in `pendingImagePromptModifier` → included in `/api/generate-images` as `prompt_modifier` → **appended** to the base prompt.

**Post-generation** (images already exist): prompt → `/api/regenerate-images` as `custom_prompt` → **replaces** the entire base prompt (uses `ImageType.EXPERIMENTAL`).

`prompt_modifier` appends; `custom_prompt` replaces entirely.
