/**
 * Copy Seller research pipeline types — mirrors the NDJSON event shapes
 * streamed by /api/research/copy-seller (backend/copy_seller.py).
 */

/** User-adjustable importances per metric; canonical shape used across the UI. */
export interface RankingWeights {
  demand: number;
  competition: number;
  velocity: number;
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
  weights?: RankingWeights | null;
  api_calls_made: number;
  api_calls_used_today: number;
  product_candidates: ProductCandidate[];
}

/** Summary of a persisted Pipeline Run, from GET /api/research/copy-seller/runs. */
export interface PipelineRunSummary {
  run_id: string;
  seller: string;
  timestamp: string;
  weights: RankingWeights | null;
  candidate_count: number;
}

/** A full persisted Pipeline Run, from GET /api/research/copy-seller/runs/<id>. */
export interface PipelineRun {
  run_id: string;
  seller: string;
  timestamp: string;
  inputs: { top_n: number; k: number; min_sold: number };
  weights: RankingWeights | null;
  product_candidates: ProductCandidate[];
}
