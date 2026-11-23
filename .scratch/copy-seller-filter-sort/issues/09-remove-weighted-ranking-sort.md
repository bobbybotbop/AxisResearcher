# 09: Remove weighted ranking; sort survivors by a single chosen metric

**What to build:** The Copy Seller pipeline stops computing a composite weighted
score. The composite score, rank number, and min-max normalization are removed.
Each Product Candidate row shows raw metric values only (no score, no rank, no
normalized values). A "sort by" control orders the surviving candidates
greatest-to-least by one user-picked metric. The `RankingWeights` type and the
weighted-sum ranking util are deleted. The backend no longer accepts or persists
`weights`; legacy saved runs still load, with any stored weights ignored.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] No composite score, rank number, or normalization anywhere in the results UI
- [ ] Each Product Candidate row shows raw metric values only
- [ ] A sort-by control orders candidates greatest-to-least by one chosen metric
- [ ] `RankingWeights` and the weighted-sum ranking util are deleted
- [ ] Backend `run_copy_seller` and the `/api/research/copy-seller` endpoint no longer accept or persist `weights`
- [ ] Legacy saved runs (with a `weights` field) still load, weights ignored
- [ ] All weight-related code removed from the project
