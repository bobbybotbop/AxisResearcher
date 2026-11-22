interface ListingCardSkeletonProps {
  viewMode: "compact" | "detailed";
}

function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded bg-surface-muted ${className}`} />;
}

/**
 * Skeleton placeholder for a history listing card while listings load (ADR
 * 0002 §7 — card/row layouts get skeletons, not spinners). Mirrors the real
 * CompactListingRow / GeneratedListingCard shapes so the list doesn't shift
 * when content arrives.
 */
export default function ListingCardSkeleton({ viewMode }: ListingCardSkeletonProps) {
  if (viewMode === "compact") {
    return (
      <div
        aria-hidden="true"
        className="flex w-full overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm"
      >
        <div className="h-20 w-24 shrink-0 bg-surface-muted" />
        <div className="flex min-w-0 flex-1 flex-col justify-center gap-2 px-3 py-2">
          <Pulse className="h-4 w-2/3" />
          <Pulse className="h-3 w-1/2" />
        </div>
        <div className="flex shrink-0 items-center px-3">
          <Pulse className="h-5 w-16" />
        </div>
      </div>
    );
  }

  return (
    <div
      aria-hidden="true"
      className="flex w-full flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm md:flex-row md:items-stretch"
    >
      <div className="w-full shrink-0 border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r">
        <div className="aspect-square w-full bg-surface-muted" />
        <div className="border-t border-border-default p-3 sm:p-4">
          <Pulse className="h-9 w-full" />
        </div>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-4 p-4 sm:p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <Pulse className="h-6 w-3/4" />
            <Pulse className="mt-2 h-3 w-1/2" />
          </div>
          <Pulse className="h-7 w-20" />
        </div>
        <div className="flex flex-col gap-3 border-t border-border-default pt-4">
          <div className="flex gap-2">
            <Pulse className="h-20 w-20" />
            <Pulse className="h-20 w-20" />
            <Pulse className="h-20 w-20" />
          </div>
          <Pulse className="h-24 w-full" />
        </div>
      </div>
    </div>
  );
}
