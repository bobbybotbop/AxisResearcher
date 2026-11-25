import type {
  MetricRange,
  MetricRangeFilters,
  ProductCandidate,
} from "../types/research";

/**
 * A Product Candidate passes a MetricRange when its value is inside every set
 * bound. A null bound means "any" on that side. A null metric value (e.g.
 * Demand Coefficient when Demand collection was off, or Sold Velocity when the
 * listing age is unknown) is treated as "not collected" and passes — we never
 * filter out a candidate on a metric we don't have a value for.
 */
function passesRange(value: number | null, range: MetricRange): boolean {
  if (range.min === null && range.max === null) return true;
  if (value === null || !Number.isFinite(value)) return true;
  if (range.min !== null && value < range.min) return false;
  if (range.max !== null && value > range.max) return false;
  return true;
}

/**
 * Drop Product Candidates whose metric values fall outside any set range.
 * Pure: operates on the cached candidates array, so editing a range re-filters
 * live without a pipeline re-run.
 */
export function filterCandidates(
  candidates: ProductCandidate[],
  ranges: MetricRangeFilters,
): ProductCandidate[] {
  return candidates.filter(
    (c) =>
      passesRange(c.demand_coefficient ?? null, ranges.demand) &&
      passesRange(c.competition_count ?? null, ranges.competition) &&
      passesRange(c.sold_velocity ?? null, ranges.velocity),
  );
}
