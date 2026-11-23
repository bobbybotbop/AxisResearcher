/** Mirrors SELLER_SETUP_CALLS in backend/constants/research.py. */
export const SELLER_SETUP_CALLS = 5;

/**
 * Mirrors estimate_api_call_cost in backend/copy_seller.py:
 * N×(1 + K·[demand on]) + setup. The K sold-sum getItem lookups only run when
 * Demand collection is on; the one search per product always runs.
 */
export function estimateApiCallCost(
  topN: number,
  k: number,
  collectDemand = true,
): number {
  return topN * (1 + (collectDemand ? k : 0)) + SELLER_SETUP_CALLS;
}
