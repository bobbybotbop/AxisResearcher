# 04: Research Pipeline UI — run form, progress, raw results

**What to build:** A Research Pipeline section under the Testing tab. It has a run form (seller username, top-N, K, min-sold threshold, three weight sliders), shows the estimated API-call cost computed from N and K, streams live progress while a run executes, and renders the streamed Product Candidates as ProductCandidateRows mirroring the history-tab compact row layout (thumbnail, title, key fields) showing the raw metrics. Weight sliders are present but do not yet re-rank live.

**Blocked by:** 03

**Status:** resolved

- [ ] Research Pipeline section renders under the Testing tab
- [ ] Run form exposes seller, top-N, K, min-sold, and three weight sliders
- [ ] Estimated API-call cost shown, computed from N and K
- [ ] Live progress streams during a run via the existing progress pattern
- [ ] Streamed Product Candidates render as ProductCandidateRows mirroring the history-tab compact row
- [ ] Each row shows the raw metrics
