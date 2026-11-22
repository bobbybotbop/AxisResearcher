# Glossary

## 3D File Finder
The multi-step wizard (in the Testing tab: `ImageSearchSteps.tsx` + `TitleSearchPipeline.tsx` + the shared `SharedDownloadRender.tsx`) that goes from an eBay listing to a downloaded 3D printable model. It contains two selectable pipelines — Image Search and Title Search — that share a common download (Step 3) and Studio Render (Step 4) stage.

## Image Search Pipeline
The original 3D File Finder flow: Step 1 fetch eBay photos, Step 2 reverse image search via SerpAPI with Blacklisted Sites filtered server-side, then shared Steps 3–4.

## Title Search Pipeline
The newer 3D File Finder flow: paste an eBay link → fetch the listing title → optimize the title via Claude Haiku (strip sales terms like quantity, color, condition) → append " 3d file" → Google text search via SerpAPI, excluding Blacklisted Sites (and Yeggi) in the query itself → pick the best link by site priority → Image Confirmation → shared Steps 3–4. If no viable whitelisted link is found, the search retries once automatically with a shortened query (first version/model code only, unnecessary words cut via Haiku).

## Blacklisted Site
A domain that search results must never come from: marketplaces (eBay, Amazon, Walmart, Etsy, AliExpress, Temu, Mercari, Poshmark) and Reddit. Also treated as blacklisted: a link on a whitelisted 3D file site that doesn't point to a specific product page (e.g. a Printables tag page) — such links can't be downloaded, so they're excluded the same way. Blacklisted Sites are excluded from Title Search Pipeline queries and filtered out of both pipelines' results server-side. Counterpart to the whitelisted 3D file sites ranked by Site Priority.

## Image Confirmation
A non-blocking step in the Title Search Pipeline after a candidate link is chosen. All eBay listing photos and all main model images from the candidate 3D file site page are downloaded and compared using perceptual hash (pHash) on the backend. The result labels the saved 3D file as either "Confirmed image match" or "Unconfirmed title match" — it does not block the download.

## Site Image Scraper
A per-site module (parallel to the per-site downloaders) that extracts the main model gallery images from a 3D file site page. Uses the most reliable deterministic method per site — data API where available, DOM scraping where necessary:
- **Thingiverse**: v2 API `things/{id}/complete` → `images[].url`
- **Printables**: GraphQL `images[].filePath` → `media.printables.com/{filePath}`
- **Thangs**: `__NEXT_DATA__` JSON → `attachments[].imageUrl`
- **MakerWorld**: SSR `div.swiper-slide > img.swiper-lazy` src (strip resize params) or design API `pictures[]`
- **Cults3D**: lightbox `div.slides__slide img` `data-src` → `fbi.cults3d.com` originals
Each scraper has its own status/probe (like the download probes) so site changes are detected.

## Saved 3D File
A persisted record of a downloaded 3D file, stored in the SQLite database and browsable in the "Saved 3D Files" tab. Contains: the downloaded 3D file (on disk, path in DB), the source site URL, the eBay listing URL (stored as a link, photos not saved), the eBay listing title, the match label ("Confirmed image match" or "Unconfirmed title match"), the pipeline that produced it (Image Search or Title Search), images from the 3D file website stored locally (not rendered images), and a timestamp.

## Saved 3D Files Tab
A new top-level tab in the app, laid out like the History tab: searchable, paginated list of Saved 3D File cards with title, source site, match label, timestamp, and a gallery of the source site's images. No 3D rendered images are stored here.

## Site Priority
The user-defined ordering of 3D file sites (Thingiverse, Printables, MakerWorld, Cults3D, Thangs, Yeggi) that determines which candidate link is chosen when multiple whitelisted sites appear in search results. Editable via drag-and-drop in the Settings tab using `@hello-pangea/dnd` (the project's existing DnD library). Applies to both pipelines' result ranking. Stored in localStorage.

## Studio Render (Step 4)
The fourth step of the 3D File Finder: renders the downloaded 3D model into a professional product photo — pure white background, soft grounding shadow, "Amazon hero shot" look — via headless Blender on the backend. Exactly one camera angle per render (for now).

## Render Job
An asynchronous unit of work: the frontend submits a render request (model file + settings + camera), receives a task id, and polls for completion. Mirrors the existing `/api/generate-images` task-id pattern.

## Render Settings
The user-configurable inputs to a Studio Render, persisted in `listingPreferences.json`: material (color, glossiness, Surface Finish), lighting (key/fill/rim intensities, ambient strength), shadows (on/off, softness), exposure, square resolution, field of view, and Shot Mode with its Camera Rig. Background is fixed pure white; light positions and color management are fixed. Rendering is CPU-only (Cycles); there is deliberately no GPU mode — this machine has only an integrated AMD GPU, which Cycles cannot use.

## Render Profile
A named snapshot of the full Render Settings, saved in `listingPreferences.json` under `render_profiles`. The always-present default entry is "Current Settings" — the flat settings themselves. Selecting a profile in Step 4 copies its values into Current Settings (the selection is sticky), so the render path always reads the flat settings regardless of profiles. Profiles are created and edited in the Profile Editor; editing "Current Settings" writes back to the flat settings.

## Profile Editor
The in-place editor view within Step 4 (not a route, not a floating modal) for creating or editing a Render Profile: a square 3D viewer preloaded with a bundled 3DBenchy, a settings panel to its right, a Render button that runs a real Blender Render Job on the benchy with the editor's current values, and Save / "Save as new profile" buttons. "Save as new profile" opens a name-input modal; in edit mode "Save" overwrites the profile in place.

## Surface Finish
The material texture of a Studio Render: Smooth Plastic (plain Principled BSDF) or Layer Lines (procedural FDM layer-line bump). Layer Lines exposes two sub-settings: layer height (labeled in real FDM layer heights, 0.08–0.4mm, default 0.2mm) and line depth (bump strength).

## Shot Mode
Single (one camera angle per render, captured ephemerally from the Step 4 preview — today's behavior) or Multi (a Camera Rig of N cameras producing N images per Render click, run as sequential Render Jobs and shown as an image grid). Shot Mode and the rig are saved in the Render Profile.

## Camera Rig
The ordered set of cameras in Multi Shot Mode. Each camera is defined by azimuth (orbit around the model, −360° to +360°; negative values orbit counterclockwise) and elevation (height, −90° to +90°); roll is fixed at 0 (horizon always level) and distance/look-at stay automatic. A preset library of named angles (front, top, left, right, bottom, back, front-right, back-left, front-top-left, back-bottom-right) provides one-click starting points.

## Rig Overview
In the Profile Editor's Multi Shot Mode, the main square three.js view showing the benchy with every rig camera's frustum and sight line wireframed. Below it, a strip of small per-camera POV thumbnails (framing-only lightweight previews) — clicking one selects that camera for editing and highlights its frustum.

## Render Mesh
The single canonical mesh both the Step 4 preview and the Blender render work from. Downloaded files in formats Blender 3.6 imports natively (.stl, .obj, .ply) are used as-is; .step/.stp are normalized to .stl with gmsh (pip wheel) and .3mf with trimesh (pure-Python pip package) — both are project dependencies, not machine installs — guaranteeing the preview and the render always show the same geometry. .amf files are not supported at all: they are excluded from the preferred download extensions and rejected with a clear ".amf is not supported" error already in the download step.

## SQLite Database
The single persistent store for all structured application data, replacing `listingPreferences.json`, `Generated_Listings/*.json`, `logs.ndjson`, and `prompts/*.txt`. Uses Python's stdlib `sqlite3` (no ORM). Binary files (generated images, 3D files) stay on disk; the database stores their paths. Secrets remain in `.env`. Frontend localStorage is unaffected.

## Data Browser Tab
A new top-level tab for debugging: a file-browser-style interface over the SQLite database. Pick a table from a sidebar (listings, preferences, logs, prompts, saved_3d_files), see paginated rows, click to expand full JSON detail. No SQL query interface — purely visual browsing.

## Testing Tab Philosophy
The Testing tab is a development sandbox: every control, threshold, and intermediate value should be exposed and editable so features can be debugged and tuned before promotion to the main workflow. Nothing in the Testing tab should be a hidden constant.

## Research Pipeline
A named, multi-step market-research workflow under the Testing tab, distinct from the 3D File Finder pipelines (which find 3D files). A Research Pipeline takes a typed input (e.g. an eBay seller), collects raw per-product metrics, and produces a ranked list of Product Candidates. "Copy Seller" is the first Research Pipeline.

## Pipeline Run
A persisted record of one execution of a Research Pipeline: its input, the ranking weights used, a timestamp, and the resulting ranked Product Candidates. Runs are saved so different weight configurations can be compared.

## Product Candidate
A single product identified by a Research Pipeline, carrying: the seller's representative eBay listing link, a simplified search phrase, and its collected market metrics. The ranked unit of a Pipeline Run.

## Demand Coefficient
The ratio of active listings to sold listings for a Product Candidate's simplified search phrase — a proxy for how saturated vs. in-demand a product is.

## Competition Count
The number of active listings also selling the same product (matching the Product Candidate's simplified search phrase). A standalone metric, separate from the Demand Coefficient.

## Sold Velocity
A Product Candidate's total sold quantity divided by its listing age (estimatedSoldQuantity ÷ days since itemCreationDate, both from the eBay Browse API). A proxy for how fast a product sells. Caveat: estimatedSoldQuantity is an estimate, and itemCreationDate resets on relist.

## Ranking Weights
The user-adjustable importances applied to each metric to compute a Product Candidate's rank. Weights affect scoring only, not metric collection, so re-weighting re-ranks instantly from cached metrics. Each metric is min-max normalized to 0–1 across the run's products before weighting, so a given weight means the same thing on every slider; raw values are shown alongside normalized ones. All metrics are oriented "higher is better" (Competition Count is inverted during normalization).

## eBay API Budget
The app's eBay API usage is capped at roughly 5,000 calls per day. Research Pipelines must be designed to bound their per-run call count (top-N listing cap, top-K sold-sum cap) so a run cannot blow the daily budget.

## Camera Intent
The camera state captured from the Step 4 live preview when the user presses Render: viewing direction, look-at target, and field of view. The backend reproduces the *direction and FOV* but auto-computes the distance so the whole model is always framed, regardless of the model's original scale or origin.

## Task
The atomic unit of async work in the status system. A Task has an id, a name, a status (pending / running / success / error), optional progress (current / total), and an optional error message. A Task may be standalone (e.g. "Generate images") or part of a Pipeline. Replaces the ad-hoc `is*` boolean flags and one-off progress objects.

## Pipeline
A named, ordered sequence of Tasks with a current index. A Pipeline renders as a step tracker (e.g. the Create workflow); a standalone Task renders as a progress bar or toast. Replaces the four parallel `ProgressState` objects.

## Status Store
The single frontend store that owns all Task and Pipeline state. Every async operation in the app reports through it, replacing the fragmented `useState` booleans, `ToastContainer`, and `StartupToasts` with one pipeline. Scope is strictly *waiting-state* UI: spinners, progress bars, skeletons, toasts, and step statuses while the user waits. It never touches feature inputs or outputs (whitelisted results, candidate lists, form values, intermediate debug values) — those stay in the features that own them.

## PipelineTracker
The single component that renders a Pipeline as a step tracker: per-step status icon (pending / running / done / error), step name, and the active step's determinate progress as text ("3 of 8"). It is a pure status renderer — it can display any step's waiting state regardless of whether that step also has a bespoke detail UI below it. Used by the Create workflow and all Testing pipelines.
