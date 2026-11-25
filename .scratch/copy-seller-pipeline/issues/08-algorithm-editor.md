# 08: Algorithm editor — weighted scoring & optimal configuration

**What to build:** Reintroduce weighted scoring as an opt-in layer on top of the
filter+sort model, behind an "algorithm editor" UI. The editor lets the user:

- Assign a weight to each Metric (Demand Coefficient, Competition Count, Sold
  Velocity) and combine them into a composite score (min-max normalized across
  the run, weighted sum — the approach removed in the filter+sort pivot).
- Save, name, and compare multiple weight configurations against the same
  cached Product Candidates, with no pipeline re-run.
- Search for an optimal configuration: sweep/optimize weights so the resulting
  ordering best matches a goal the user specifies (e.g. surface a known-good
  product, or maximize agreement with a picked subset). Define what "optimal"
  optimizes against before building the optimizer.

**Why deferred:** The filter+sort model (Metric Range Filters + a single Sort
Metric, no composite score) replaced weighted ranking as the default. Weights
were removed from the project; this task brings them back as an advanced,
optional tool rather than the primary interaction.

**Blocked by:** the filter+sort pipeline (Metric Range Filters, Sort Metric,
Date-Posted Range) being in place.

**Status:** open

- [ ] Per-metric weight inputs + composite weighted-sum score (min-max normalized)
- [ ] Save / name / load multiple weight configurations
- [ ] Compare configurations against cached candidates without re-running
- [ ] Define the optimization target for "optimal configuration"
- [ ] Weight-configuration sweep/optimizer
