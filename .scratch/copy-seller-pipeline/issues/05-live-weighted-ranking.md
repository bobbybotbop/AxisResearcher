# 05: Live weighted ranking + normalization

**What to build:** Min-max normalization of each metric to 0–1 across the run's products, weighted-sum scoring, Competition Count inverted so all metrics read "higher is better", and live re-ranking when the weight sliders move — operating on cached metrics with no re-run. Raw and normalized values are both shown per row.

**Blocked by:** 04

**Status:** resolved

- [ ] Each metric min-max normalized to 0–1 across the run's products
- [ ] Competition Count inverted during normalization (fewer competitors = higher score)
- [ ] Rank = weighted sum of normalized metrics
- [ ] Moving a weight slider re-ranks instantly from cached metrics (no re-run)
- [ ] Each row shows raw and normalized metric values
