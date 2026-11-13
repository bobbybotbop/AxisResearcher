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
  not_found_skus?: string[];
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
    default:
      return entry.error || "";
  }
}

export default function LogsTab({ onNavigateToSku, onOpenListing }: LogsTabProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

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

  const filtered =
    filter === "all" ? logs : logs.filter((e) => e.event === filter);

  function toggleRow(timestamp: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(timestamp)) {
        next.delete(timestamp);
      } else {
        next.add(timestamp);
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
        {filtered.map((entry, i) => {
          const isError = entry.status === "error";
          const isRestock = entry.event === "restock";
          const hasSku = !!entry.sku;
          const isExpanded = expandedRows.has(entry.timestamp);

          const isClickable = isRestock || (hasSku && !!onNavigateToSku);

          const handleRowClick = () => {
            if (isRestock) {
              toggleRow(entry.timestamp);
            } else if (hasSku && onNavigateToSku) {
              onNavigateToSku(entry.sku!);
            }
          };

          return (
            <div key={i} className="flex flex-col">
              <div
                className={`flex items-start gap-3 rounded-md px-3 py-2.5 text-sm ${
                  isError ? "bg-danger/5" : "hover:bg-surface-hover"
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
                {isRestock && (
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
                <div className="ml-9 mb-1 flex flex-col divide-y divide-border-default rounded-md border border-border-default">
                  {(entry.skus || []).map((sku, j) => {
                    const ebayId = (entry.ebay_ids || [])[j] ?? "";
                    return (
                      <div
                        key={j}
                        className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-hover"
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenListing(sku);
                          }}
                          className="font-medium text-text-primary hover:text-primary"
                        >
                          {sku}
                        </button>
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
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenListing(sku);
                          }}
                          className="ml-auto text-xs text-text-muted hover:text-primary"
                        >
                          View
                        </button>
                      </div>
                    );
                  })}
                  {(entry.skus || []).length === 0 && (
                    <p className="px-3 py-2 text-xs text-text-muted">No SKUs</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
