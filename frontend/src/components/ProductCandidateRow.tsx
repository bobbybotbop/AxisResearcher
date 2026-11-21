import type { ProductCandidate } from "../types/research";

interface ProductCandidateRowProps {
  candidate: ProductCandidate;
  rank: number;
}

function LinkIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M12.232 4.232a2.5 2.5 0 0 1 3.536 3.536l-1.225 1.224a.75.75 0 0 0 1.061 1.06l1.224-1.224a4 4 0 0 0-5.656-5.656l-3 3a4 4 0 0 0 .225 5.865.75.75 0 0 0 .977-1.138 2.5 2.5 0 0 1-.14-3.667l2.998-2.999Z" />
      <path d="M11.603 7.963a.75.75 0 0 0-.977 1.138 2.5 2.5 0 0 1 .14 3.667l-3 3a2.5 2.5 0 0 1-3.536-3.536l1.225-1.224a.75.75 0 0 0-1.061 1.06l-1.224 1.224a4 4 0 1 0 5.656 5.656l3-3a4 4 0 0 0-.223-5.865Z" />
    </svg>
  );
}

function formatMetric(value: number | null, digits = 2): string {
  if (value === null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

function formatPrice(value: number | null, currency: string | null): string {
  if (value === null || !Number.isFinite(value)) return "—";
  const code = currency || "USD";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${code}`;
  }
}

export default function ProductCandidateRow({
  candidate,
  rank,
}: ProductCandidateRowProps) {
  const title = candidate.title || "No title";

  return (
    <div className="flex w-full overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md">
      {/* Thumbnail */}
      <div className="relative h-20 w-24 shrink-0 bg-surface-muted">
        {candidate.image_url ? (
          <div className="flex h-full w-full items-center justify-center">
            <img
              src={candidate.image_url}
              alt={title}
              className="max-h-full max-w-full object-contain"
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            No image
          </div>
        )}
      </div>

      {/* eBay link strip */}
      <div className="flex h-20 w-8 shrink-0 border-l border-r border-border-default">
        {candidate.listing_url ? (
          <a
            href={candidate.listing_url}
            target="_blank"
            rel="noopener noreferrer"
            title="View on eBay"
            className="flex h-full w-full items-center justify-center bg-surface-muted text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
          >
            <LinkIcon />
          </a>
        ) : (
          <div className="h-full w-full bg-surface-muted" />
        )}
      </div>

      {/* Content column */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-1 px-3 py-2">
        <div className="flex shrink-0 items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className="shrink-0 rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary"
                title="Rank within this run"
              >
                #{rank}
              </span>
              <h3 className="line-clamp-1 text-base font-semibold leading-snug text-text-primary">
                {title}
              </h3>
            </div>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0 text-sm text-text-muted">
              <span
                className="whitespace-nowrap"
                title="Demand Coefficient: top-K sold sum ÷ active listings (higher is better)"
              >
                Demand {formatMetric(candidate.demand_coefficient)}
              </span>
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap"
                title="Competition Count: active listings for the search phrase (fewer is better)"
              >
                Competition {candidate.competition_count.toLocaleString()}
              </span>
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap"
                title="Sold Velocity: estimated sold ÷ listing age in days (higher is better)"
              >
                Velocity {formatMetric(candidate.sold_velocity)}/day
              </span>
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap"
                title="Estimated sold quantity on the seller's listing"
              >
                Sold {candidate.estimated_sold_quantity.toLocaleString()}
              </span>
            </p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-lg font-bold text-text-primary">
              {formatPrice(candidate.price, candidate.currency)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
