/** Mirrors SELLER_SETUP_CALLS in backend/constants/research.py. */
export const SELLER_SETUP_CALLS = 5;

/** Mirrors estimate_api_call_cost in backend/copy_seller.py: N×(1+K) + setup. */
export function estimateApiCallCost(topN: number, k: number): number {
  return topN * (1 + k) + SELLER_SETUP_CALLS;
}
