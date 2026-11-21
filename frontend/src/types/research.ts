/**
 * Copy Seller research pipeline types — mirrors the NDJSON event shapes
 * streamed by /api/research/copy-seller (backend/copy_seller.py).
 */

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
  inputs: { top_n: number; k: number; min_sold: number };
  api_calls_made: number;
  api_calls_used_today: number;
  product_candidates: ProductCandidate[];
}
