import type { MetricRangeFilters, SortMetric } from "../types/research";

/**
 * Plain-English presentation info for the three Copy Seller metrics — the
 * single source of truth for metric labels and calculation explanations.
 * Labels must stay free of internal constants and jargon (no "K", "top-N",
 * "coefficient", "velocity"); the calculation text explains exactly how the
 * backend computes each metric (backend/copy_seller.py).
 */
export interface MetricInfo {
  /** Plain-English metric name shown on cards, rows, and the sort select. */
  label: string;
  /** Exactly how the metric is calculated, shown by the "?" tooltip. */
  calculation: string;
  /** Whether "higher" or "lower" values are better, in plain English. */
  direction: string;
  /** Key of this metric's acceptable-range inputs in MetricRangeFilters. */
  rangeKey: keyof MetricRangeFilters;
}

export const METRIC_INFO: Record<SortMetric, MetricInfo> = {
  demand: {
    label: "Demand score",
    calculation:
      "We search eBay for the product's search phrase, add up the estimated " +
      "times sold across the top listings in the results (how many is set by " +
      '"Listings to check for demand"), then divide by the total number of ' +
      "active listings selling this.",
    direction: "Higher is better.",
    rangeKey: "demand",
  },
  competition: {
    label: "Listings selling this",
    calculation:
      "We search eBay for the product's search phrase and count the total " +
      "number of active listings that come up.",
    direction: "Fewer is better.",
    rangeKey: "competition",
  },
  velocity: {
    label: "Sells per day",
    calculation:
      "The seller listing's estimated times sold divided by its age in days " +
      "(today minus the date the listing was created; listings under a day " +
      "old count as one day).",
    direction: "Higher is better.",
    rangeKey: "velocity",
  },
};

/** Sort-select options in display order. */
export const SORT_OPTIONS: { value: SortMetric; label: string }[] = [
  { value: "demand", label: METRIC_INFO.demand.label },
  { value: "competition", label: METRIC_INFO.competition.label },
  { value: "velocity", label: METRIC_INFO.velocity.label },
];
