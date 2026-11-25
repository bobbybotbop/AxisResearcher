# 14: Persist filter/sort/date config in Pipeline Runs and restore on load

**What to build:** Saved Pipeline Runs record the new configuration in their
inputs: each metric's acceptable-range filter, the chosen sort metric, the
date-posted range, and the Demand collection toggle. Loading a past run restores
that exact configuration into the run form, so the run is reproducible and
configurations can be compared. (Weights were already removed in ticket 09; this
adds the new fields.)

**Blocked by:** 11, 12, 13

**Status:** ready-for-agent

- [ ] Saved runs persist metric range filters, sort metric, date-posted range, and Demand toggle in inputs
- [ ] Loading a past run restores all of these into the form
- [ ] Past-runs list/summary reflects the new config shape (no weights)
