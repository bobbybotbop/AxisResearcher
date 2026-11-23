# 06: Persist Pipeline Runs + reload/compare

**What to build:** Each Pipeline Run is saved as JSON under `Collected-Data/<seller>/` with its input, ranking weights, timestamp, and ranked Product Candidates. The UI lists past runs and can reload one (restoring its metrics and weights) so weight configurations can be compared. Milestones are logged to `logs.ndjson`.

**Blocked by:** 05

**Status:** resolved

- [ ] Each run saved as JSON under `Collected-Data/<seller>/` with input, weights, timestamp, ranked candidates
- [ ] UI lists past runs
- [ ] Reloading a past run restores its metrics and weights
- [ ] Weight configurations can be compared across runs
- [ ] Run milestones logged to `logs.ndjson`
