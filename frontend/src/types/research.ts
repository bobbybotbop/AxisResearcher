/**
 * Copy Seller research pipeline types — mirrors the NDJSON event shapes
 * streamed by /api/research/copy-seller (backend/copy_seller.py).
 */

/** Metrics a Product Candidate can be sorted by (greatest-to-least). */
export type SortMetric = "demand" | "competition" | "velocity";

/**
 * An acceptable range for one metric. Either bound may be null — a null bound
 * means "any" on that side (no filtering). Both null = the metric does not
 * filter at all.
 */
export interface MetricRange {
  min: number | null;
  max: number | null;
}

/** Per-metric acceptable ranges. A Product Candidate outside any set range is dropped. */
export interface MetricRangeFilters {
  demand: MetricRange;
  competition: MetricRange;
  velocity: MetricRange;
}

export interface ProductCandidate {
  listing_url: string;
  title: string;
  search_phrase: string;
  estimated_sold_quantity: number;
  item_creation_date: string | null;
  price: number | null;
  currency: string | null;
  image_url: string | null;
  demand_coefficient: number;
  competition_count: number;
  sold_velocity: number | null;
}

export interface CopySellerResult {
  seller: string;
  run_id?: string;
  timestamp?: string;
  inputs: { top_n: number; k: number; min_sold: number };
  api_calls_made: number;
  api_calls_used_today: number;
  product_candidates: ProductCandidate[];
}

/** Summary of a persisted Pipeline Run, from GET /api/research/copy-seller/runs. */
export interface PipelineRunSummary {
  run_id: string;
  seller: string;
  timestamp: string;
  candidate_count: number;
}

/** A full persisted Pipeline Run, from GET /api/research/copy-seller/runs/<id>. */
export interface PipelineRun {
  run_id: string;
  seller: string;
  timestamp: string;
  inputs: { top_n: number; k: number; min_sold: number };
  product_candidates: ProductCandidate[];
}
