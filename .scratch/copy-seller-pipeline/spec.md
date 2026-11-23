# Copy Seller — Research Pipeline spec

A new **Research Pipeline** section under the Testing tab. "Copy Seller" is the
first pipeline: given an eBay seller, find their best products and rank them by
adjustable demand metrics. Output is a ranked list of Product Candidates with
their eBay listing links.

## Framework

- A **Research Pipeline** is a named, multi-step market-research workflow with a
  typed input and a ranked-list output. Distinct from the 3D File Finder
  pipelines. "Copy Seller" is instance #1; the model generalizes to future
  pipelines.
- Each execution is a persisted **Pipeline Run**: input + ranking weights +
  timestamp + ranked Product Candidates. Runs are saved so weight configurations
  can be compared.
- **Metric collection is separate from ranking.** Raw metrics are fetched once
  per product and cached; the rank score is computed live in the UI from cached
  metrics + current weights. Re-weighting re-ranks instantly without re-running.

## Pipeline steps (Copy Seller)

1. **Collect the seller's listings** — Browse API `item_summary/search` with
   `filter: sellers:{username}`, paginated (existing `getItemIds` /
   `single_search_by_seller` in `backend/ebay_cli.py`).
2. **Get per-listing details** — Browse API `getItem` → `estimatedSoldQuantity`,
   `itemCreationDate`, price, images (existing `single_get_detailed_item_data`).
   Skip listings below the minimum-sold threshold.
3. **Take the top N** listings by sold quantity (N editable, default 25).
4. **Simplify each title → short search phrase.** Uses a dedicated prompt
   authored by a separate agent — see backlog ticket
   `issues/01-title-simplification-prompt.md`. Placeholder until linked.
5. **Search eBay for each phrase** and compute metrics (below).
6. **Rank** the Product Candidates by the weighted score.

## Metrics (all oriented "higher is better" after normalization)

- **Demand Coefficient** = aggregate sold ÷ active listings for the phrase.
  Aggregate sold sums `estimatedSoldQuantity` over the top K search results
  (K editable, default 20). Active listings = the search `total` count. A proxy
  (estimatedSoldQuantity is an eBay estimate, cumulative over listing life).
- **Competition Count** = number of active listings for the phrase (the search
  `total`). Inverted during normalization (fewer competitors = better).
- **Sold Velocity** = the seller listing's `estimatedSoldQuantity` ÷ listing age
  in days (`now − itemCreationDate`). Caveat: itemCreationDate resets on relist.

**Deferred:** Days Since Last Sold — no ungated eBay API (findCompletedItems
decommissioned Feb 2025; Marketplace Insights approval-gated). See backlog
ticket `issues/02-date-last-sold-metric.md`.

## Scoring

- Each metric is **min-max normalized to 0–1 across the run's products**, then
  multiplied by its weight. Raw and normalized values are both shown (Testing
  Tab Philosophy — nothing hidden).
- Rank = weighted sum. Ranks are comparable within a run, not across runs.

## Run inputs (Testing tab form)

- Seller username (text)
- Top N listings to process (default 25)
- Three weight sliders (Demand Coefficient, Competition Count, Sold Velocity)
- Minimum sold-quantity threshold (default 1) to skip dead listings
- K for the demand-coefficient sold-sum (default 20)

## eBay API budget (~5,000 calls/day)

- The run form shows an **estimated API-call cost** computed from N and K
  (≈ N×(1+K) + seller setup; ~600 calls for N=25, K=20).
- The backend tracks daily usage and **warns/blocks** when a run would exceed
  the remaining budget.

## Data flow & storage

- NDJSON-streaming endpoint `/api/research/copy-seller` using the existing
  `progress_event` / `result_event` + `fetchWithProgress` + `ProgressIndicator`
  pattern (`app.py:234-255`). Watch each product process live.
- Results written as JSON under `Collected-Data/<seller>/` (existing
  convention). Milestones logged via `log_event` to `logs.ndjson`.
- Auth via existing `helper_get_valid_token()` / auto-refresh; no new
  credentials.

## UI

- New `frontend/src/components/ResearchPipeline.tsx` under the Testing tab
  (sibling to `ThreeDFileFinder.tsx`), reusing `btnPill` / surface tokens.
- Run form (inputs above) + live progress + ranked results.
- Results rendered as a `ProductCandidateRow` mirroring the history-tab compact
  row layout (thumbnail, title, key fields, status pills), typed to Product
  Candidate and showing rank, weight-adjusted score, and the three metrics
  (raw + normalized). Weight sliders re-rank live.

## Backlog

- `issues/01-title-simplification-prompt.md` — link the title-simplification
  prompt when the separate agent delivers it.
- `issues/02-date-last-sold-metric.md` — add Days Since Last Sold once a data
  source is chosen (Marketplace Insights or browser scrape).
