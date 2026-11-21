import { useState, useEffect, useCallback } from "react";
import { RefreshCw, CheckCircle, XCircle, ChevronRight, ChevronDown, ExternalLink } from "lucide-react";
import { LOG_EVENT_LABELS, LOG_FILTER_CHIPS } from "../constants/logs";
import type { FilterOption } from "../constants/logs";

interface LogEntry {
  event: string;
  status?: string;
  sku?: string;
  title?: string;
  ebayListingId?: string;
  sourceListingId?: string;
  source?: string;
  skus?: string[];
  ebay_ids?: string[];
  failed_skus?: string[];
  failed_errors?: Record<string, string[]>;
  not_found_skus?: string[];
  newly_inactive_skus?: string[];
  updated_skus?: string[];
  removed_titles?: Record<string, string>;
  quantity?: number;
  count?: number;
  error?: string;
  timestamp: string;
  [key: string]: unknown;
}

interface LogsTabProps {
  onNavigateToSku?: (sku: string) => void;
  onOpenListing: (sku: string) => void;
}

function formatTimestamp(iso: string) {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getEntryDetail(entry: LogEntry): string {
  switch (entry.event) {
    case "draft_created":
      return `${entry.sku}${entry.sourceListingId ? ` from eBay ${entry.sourceListingId}` : ""}`;
    case "draft_completed":
      return `${entry.sku}${entry.title ? ` — ${entry.title}` : ""}`;
    case "upload":
      return [
        entry.sku,
        entry.title ? `— ${entry.title}` : null,
        entry.ebayListingId ? `(#${entry.ebayListingId})` : null,
      ]
        .filter(Boolean)
        .join(" ");
    case "restock": {
      const src = entry.source === "auto" ? "Auto" : "Manual";
      const count = (entry.skus || []).length;
      const failCount = (entry.failed_skus || []).length;
      return `${src} — ${count} listing(s) → qty ${entry.quantity}${failCount ? `, ${failCount} failed` : ""}`;
    }
    case "import":
      return `${entry.count} listing(s) imported`;
    case "sync_active":
      return `${entry.active ?? 0} active · ${entry.newly_inactive ?? 0} newly inactive · ${entry.updated ?? 0} updated`;
    default:
      return entry.error || "";
  }
}

/**
 * One headed group of SKU rows inside an expanded log panel.
 * Generic so any event type (restock, sync, import) can declare its own sections.
 */
interface SkuSection {
  heading: string;
  skus: string[];
  /** Parallel to skus: eBay listing ID to link out to ("" = no link). */
  ebayIds?: string[];
  /** Per-SKU exact error strings, rendered under the SKU (danger styling). */
  errors?: Record<string, string[]>;
  /** Visual variant: "default" or "danger" (failed rows). */
  variant?: "default" | "danger";
  /** Show a View button that opens the listing. */
  showView?: boolean;
  /** Resolve a display title for a SKU (rendered next to it when present). */
  titleFor?: (sku: string) => string | undefined;
}

/**
 * Reusable multi-section expand panel: renders a list of headed SKU-row groups.
 * Sections with zero SKUs are omitted entirely.
 */
function SkuSectionPanel({
  sections,
  onOpenListing,
}: {
  sections: SkuSection[];
  onOpenListing: (sku: string) => void;
}) {
  const visible = sections.filter((s) => s.skus.length > 0);
  if (visible.length === 0) {
    return (
      <div className="ml-9 mb-1 rounded-md border border-border-default">
        <p className="px-3 py-2 text-xs text-text-muted">No SKUs</p>
      </div>
    );
  }
  return (
    <div className="ml-9 mb-1 flex flex-col gap-2">
      {visible.map((section) => (
        <div
          key={section.heading}
          className="flex flex-col rounded-md border border-border-default"
        >
          <p
            className={`px-3 pt-2 pb-1 text-xs font-semibold uppercase tracking-wide ${
              section.variant === "danger" ? "text-danger" : "text-text-muted"
            }`}
          >
            {section.heading}
          </p>
          <div className="flex flex-col divide-y divide-border-default">
            {section.skus.map((sku, j) => {
              const ebayId = section.ebayIds?.[j] ?? "";
              const skuErrors = section.errors?.[sku] ?? [];
              const title = section.titleFor?.(sku);
              return (
                <div
                  key={sku}
                  className="flex flex-col gap-0.5 px-3 py-2 text-sm hover:bg-surface-hover"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`font-medium ${
                        section.variant === "danger" ? "text-danger" : "text-text-primary"
                      }`}
                    >
                      {sku}
                    </span>
                    {title && (
                      <span className="truncate text-text-secondary">{title}</span>
                    )}
                    {ebayId && (
                      <a
                        href={`https://www.ebay.com/itm/${ebayId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-0.5 text-xs text-text-muted hover:text-primary"
                      >
                        <ExternalLink size={11} />
                        {ebayId}
                      </a>
                    )}
                    {section.showView && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpenListing(sku);
                        }}
                        className="ml-auto text-xs text-text-muted hover:text-primary"
                      >
                        View
                      </button>
                    )}
                  </div>
                  {skuErrors.map((msg, k) => (
                    <p key={k} className="text-xs text-danger/80">
                      {msg}
                    </p>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Build the expand-panel sections for a restock log entry. */
function restockSections(
  entry: LogEntry,
  titleFor: (sku: string) => string | undefined,
): SkuSection[] {
  const notFound = entry.not_found_skus || [];
  const notFoundSet = new Set(notFound);
  // Failed = failed_skus minus not-found (not-found SKUs get their own section).
  const failed = (entry.failed_skus || []).filter((s) => !notFoundSet.has(s));
  return [
    {
      heading: "Restocked",
      skus: entry.skus || [],
      ebayIds: entry.ebay_ids || [],
      showView: true,
      titleFor,
    },
    {
      heading: "Failed",
      skus: failed,
      errors: entry.failed_errors || {},
      variant: "danger",
    },
    {
      heading: "Not found on eBay",
      skus: notFound,
    },
  ];
}

/** Build the expand-panel sections for a sync_active log entry. */
function syncActiveSections(
  entry: LogEntry,
  titleFor: (sku: string) => string | undefined,
): SkuSection[] {
  return [
    {
      heading: "Newly inactive",
      skus: entry.newly_inactive_skus || [],
      titleFor,
    },
    {
      heading: "Updated",
      skus: entry.updated_skus || [],
      showView: true,
      titleFor,
    },
  ];
}

export default function LogsTab({ onNavigateToSku, onOpenListing }: LogsTabProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [titlesBySku, setTitlesBySku] = useState<Map<string, string>>(new Map());

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch("/api/logs");
      if (!res.ok) throw new Error(`Failed to load logs (${res.status})`);
      const data = await res.json() as { logs?: LogEntry[] };
      setLogs(data.logs || []);
    } catch (err) {
      setFetchError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/listings");
        if (!res.ok) return;
        const data = await res.json() as { listings?: { sku?: string; title?: string }[] };
        if (cancelled) return;
        const map = new Map<string, string>();
        for (const listing of data.listings || []) {
          if (listing.sku && listing.title) map.set(listing.sku, listing.title);
        }
        setTitlesBySku(map);
      } catch {
        // Title resolution is best-effort; rows fall back to SKU-only display.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function titleFor(sku: string, entry: LogEntry): string | undefined {
    return titlesBySku.get(sku) ?? entry.removed_titles?.[sku];
  }

  const filtered =
    filter === "all" ? logs : logs.filter((e) => e.event === filter);

  function toggleRow(rowKey: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(rowKey)) {
        next.delete(rowKey);
      } else {
        next.add(rowKey);
      }
      return next;
    });
  }

  return (
    <div className="flex flex-col py-6 px-2">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-text-primary">Activity Log</h1>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-border-default px-3 py-1.5 text-sm text-text-muted hover:text-text-primary hover:bg-surface-hover disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {LOG_FILTER_CHIPS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.key
                ? "bg-primary/10 text-primary"
                : "border border-border-default text-text-muted hover:bg-surface-hover hover:text-text-primary"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {fetchError && (
        <div className="mb-4 rounded-md bg-danger/10 px-4 py-3 text-sm text-danger">
          {fetchError}
        </div>
      )}

      {!loading && filtered.length === 0 && !fetchError && (
        <p className="py-8 text-center text-sm text-text-muted">
          No log entries yet.
        </p>
      )}

      <div className="flex flex-col gap-1">
        {filtered.map((entry, index) => {
          const rowKey = `${entry.timestamp}:${entry.event}:${index}`;
          const isError = entry.status === "error";
          const isRestock = entry.event === "restock";
          const isSyncActive = entry.event === "sync_active";
          // Old sync_active entries (counts only, no SKU lists) stay one-liners.
          const isSyncActiveExpandable =
            isSyncActive &&
            ((entry.newly_inactive_skus || []).length > 0 ||
              (entry.updated_skus || []).length > 0);
          const isExpandable = isRestock || isSyncActiveExpandable;
          const hasSku = !!entry.sku;
          const isExpanded = expandedRows.has(rowKey);

          const isClickable = isExpandable || (hasSku && !!onNavigateToSku);

          const handleRowClick = () => {
            if (isExpandable) {
              toggleRow(rowKey);
            } else if (hasSku && onNavigateToSku) {
              onNavigateToSku(entry.sku!);
            }
          };

          return (
            <div key={rowKey} className="flex flex-col">
              <div
                className={`flex items-start gap-3 rounded-md px-3 py-2.5 text-sm ${
                  isError ? "bg-danger/5 hover:bg-danger/10" : "hover:bg-surface-hover"
                } ${isClickable ? "cursor-pointer" : ""}`}
                onClick={isClickable ? handleRowClick : undefined}
              >
                <span className="mt-0.5 shrink-0">
                  {isError ? (
                    <XCircle size={15} className="text-danger" />
                  ) : (
                    <CheckCircle size={15} className="text-success" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <span
                    className={`font-medium ${
                      isError ? "text-danger" : "text-text-primary"
                    }`}
                  >
                    {LOG_EVENT_LABELS[entry.event] ?? entry.event}
                    {entry.event === "restock" && entry.source === "auto" && (
                      <span className="ml-1.5 text-xs font-normal text-text-muted">
                        (auto)
                      </span>
                    )}
                  </span>
                  <span className="ml-2 truncate text-text-secondary">
                    {getEntryDetail(entry)}
                  </span>
                  {isError && entry.error && (
                    <p className="mt-0.5 truncate text-xs text-danger/80">
                      {entry.error}
                    </p>
                  )}
                </div>
                <span className="shrink-0 whitespace-nowrap text-xs text-text-muted">
                  {formatTimestamp(entry.timestamp)}
                </span>
                {isExpandable && (
                  <span className="shrink-0 text-text-muted">
                    {isExpanded ? (
                      <ChevronDown size={14} />
                    ) : (
                      <ChevronRight size={14} />
                    )}
                  </span>
                )}
              </div>

              {isRestock && isExpanded && (
                <SkuSectionPanel
                  sections={restockSections(entry, (sku) => titleFor(sku, entry))}
                  onOpenListing={onOpenListing}
                />
              )}

              {isSyncActiveExpandable && isExpanded && (
                <SkuSectionPanel
                  sections={syncActiveSections(entry, (sku) => titleFor(sku, entry))}
                  onOpenListing={onOpenListing}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
