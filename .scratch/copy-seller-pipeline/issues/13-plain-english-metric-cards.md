# 13: Plain-English metric cards with calculation tooltips

**What to build:** Each metric becomes one self-contained card in the run form,
grouping: its plain-English label, a "?" tooltip explaining exactly how the
metric is calculated, its collection toggle (Demand score only), and its
acceptable-range inputs. This replaces the scattered separate controls (the old
weight-slider row and the standalone K / threshold inputs' jargon). Labels read
in plain English with no internal constants or jargon: "Demand score", "Listings
selling this", "Sells per day", and supporting inputs renamed likewise (e.g.
"Listings to analyze" for top-N, "Listings to check for demand" for K, "Minimum
times sold" for min-sold).

**Blocked by:** 10, 11

**Status:** ready-for-agent

- [ ] One card per metric grouping label + "?" tooltip + toggle (Demand only) + range inputs
- [ ] "?" tooltip on each metric explains exactly how it is calculated
- [ ] Labels are plain English; no internal constants/jargon (Demand score, Listings selling this, Sells per day)
- [ ] Supporting inputs renamed to plain English (top-N, K, min-sold)
- [ ] Replaces the previous separate/scattered controls
