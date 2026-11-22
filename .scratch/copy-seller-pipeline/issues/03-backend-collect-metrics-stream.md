# 03: Copy Seller backend — collect, metrics, stream

**What to build:** A `/api/research/copy-seller` NDJSON-streaming endpoint. Given a seller username, top-N, K, and min-sold threshold, it collects the seller's listings, fetches per-listing details, computes the three raw metrics per Product Candidate (Demand Coefficient via top-K sold-sum ÷ active listings, Competition Count, Sold Velocity), tracks daily eBay API-call usage, and streams progress events plus the raw (unranked) Product Candidates. Verifiable by curling the endpoint and watching NDJSON events stream.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] Endpoint accepts seller username, top-N (default 25), K (default 20), min-sold threshold (default 1)
- [ ] Collects the seller's listings and per-listing details (sold quantity, creation date, price, images)
- [ ] Skips listings below the min-sold threshold; takes top N by sold quantity
- [ ] Simplifies each title to a search phrase (placeholder until ticket 07)
- [ ] Computes Demand Coefficient (top-K sold-sum ÷ active), Competition Count, Sold Velocity per product
- [ ] Tracks daily eBay API-call usage and warns/blocks when a run would exceed the ~5000/day budget
- [ ] Streams progress events and final raw Product Candidates as NDJSON
