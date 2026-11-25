# 10: Decouple Demand score collection behind a toggle; cost model follows

**What to build:** A "Demand score" on/off control in the run form. When off,
the pipeline skips the K per-product sold-sum lookups but still does the one
search per product (which yields the Competition Count / "Listings selling this"
for free), cutting per-product cost from (1+K) to 1 API call. The estimated-cost
display and the backend daily-budget check both recompute as
`N×(1 + K·[demand on]) + setup`, updating live as the toggle changes. When
Demand collection is off, the Demand value shows as not-collected in result
rows.

**Blocked by:** 09

**Status:** ready-for-agent

- [ ] A Demand score on/off toggle in the run form
- [ ] When off, the pipeline skips the K sold-sum getItem lookups per product
- [ ] When off, the pipeline still performs the one search per product (Competition Count still collected)
- [ ] Estimated-cost display recomputes as N×(1 + K·[demand on]) + setup, live
- [ ] Backend budget check uses the same demand-aware cost model
- [ ] Demand value shows as not-collected in rows when collection is off
