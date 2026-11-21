/**
 * Live weighted ranking for Product Candidates (Research Pipeline).
 *
 * Pure client-side ranking: raw metrics are collected once per run and cached;
 * these helpers re-normalize and re-score from the cached metrics whenever the
 * Ranking Weights change, with no pipeline re-run.
 *
 * Every metric is min-max normalized to 0–1 across the run's products and
 * oriented "higher is better" (Competition Count is inverted: fewer
 * competitors = higher normalized score). Degenerate convention: when all
 * values of a metric are equal, every product normalizes to 1 — an
 * all-equal metric gives no product an edge, and 1 keeps the metric's
 * weight meaningful in the weighted sum rather than zeroing it out.
 */
import type { ProductCandidate, RankingWeights } from "../types/research";

export type { RankingWeights };

export interface NormalizedMetrics {
  demand: number;
  competition: number;
  velocity: number;
}

export interface RankedCandidate {
  candidate: ProductCandidate;
  normalized: NormalizedMetrics;
  score: number;
  rank: number;
}

/** Min-max normalize one metric to 0–1; all-equal values normalize to 1. */
function normalizeValues(values: number[]): number[] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  if (span === 0) return values.map(() => 1);
  return values.map((v) => (v - min) / span);
}

/**
 * Min-max normalize each metric across the run's products. Competition Count
 * is inverted (fewer competitors = higher score). A null Sold Velocity is
 * treated as 0 — the worst case, since a missing age means no evidence of
 * sales pace.
 */
export function normalizeMetrics(
  candidates: ProductCandidate[],
): NormalizedMetrics[] {
  const demand = normalizeValues(candidates.map((c) => c.demand_coefficient));
  // Negate Competition Count before normalizing so fewer competitors = higher
  // normalized score, and the all-equal degenerate convention (→ 1) holds.
  const competition = normalizeValues(
    candidates.map((c) => -c.competition_count),
  );
  const velocity = normalizeValues(
    candidates.map((c) => c.sold_velocity ?? 0),
  );
  return candidates.map((_, i) => ({
    demand: demand[i],
    competition: competition[i],
    velocity: velocity[i],
  }));
}

/** Weighted sum of the three normalized metrics. */
export function scoreCandidate(
  normalized: NormalizedMetrics,
  weights: RankingWeights,
): number {
  return (
    normalized.demand * weights.demand +
    normalized.competition * weights.competition +
    normalized.velocity * weights.velocity
  );
}

/**
 * Score every candidate and sort by score descending; rank is 1-based.
 * Ties keep the candidates' original relative order (stable sort).
 */
export function rankCandidates(
  candidates: ProductCandidate[],
  weights: RankingWeights,
): RankedCandidate[] {
  const normalizedRows = normalizeMetrics(candidates);
  return candidates
    .map((candidate, i) => ({
      candidate,
      normalized: normalizedRows[i],
      score: scoreCandidate(normalizedRows[i], weights),
      rank: 0,
    }))
    .sort((a, b) => b.score - a.score)
    .map((row, i) => ({ ...row, rank: i + 1 }));
}
