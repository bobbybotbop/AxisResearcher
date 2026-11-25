# 11: Per-metric acceptable-range filters

**What to build:** Each metric (Demand score, Listings selling this, Sells per
day) gets an optional minimum/maximum acceptable-range input. A Product
Candidate whose metric value falls outside a set range is dropped from the
results. An unset bound means "any" — that metric does not filter. The Demand
score range only applies when Demand collection is on. Filtering operates on the
cached candidates, so editing a range re-filters live without a pipeline re-run.

**Blocked by:** 09

**Status:** ready-for-agent

- [ ] Each metric has an optional min and max range input
- [ ] Candidates outside any set range are removed from results
- [ ] An unset bound means "any" (no filtering on that metric)
- [ ] Demand range applies only when Demand collection is on
- [ ] Editing a range re-filters live from cached candidates (no re-run)
