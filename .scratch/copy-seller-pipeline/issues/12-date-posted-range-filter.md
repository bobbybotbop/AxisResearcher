# 12: Date-posted range filter on the seller's listings

**What to build:** A two-sided calendar date-range picker in the run form,
defaulting to today→today. Picking a past start day sets the range from that day
to today; both ends are adjustable. The pipeline filters the seller's own
listings by their posted date (itemCreationDate) to those within the range,
applied before the top-N cut and before any metric is computed. All metrics are
then computed only on the date-filtered pool. Because this is a collection-time
filter, applying it requires a pipeline re-run (it does not re-filter cached
candidates live).

**Blocked by:** 09

**Status:** ready-for-agent

- [ ] Two-sided calendar date-range picker, default today→today
- [ ] Picking a past start day sets end to today; both ends adjustable
- [ ] Pipeline filters the seller's listings by itemCreationDate to within the range
- [ ] Date filter applies before the top-N cut and before metric computation
- [ ] Applying the date filter requires a re-run (collection-time, not live)
