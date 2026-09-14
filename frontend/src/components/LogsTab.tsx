import { useState, useEffect, useCallback } from "react";
import { RefreshCw, CheckCircle, XCircle } from "lucide-react";

interface LogEntry {
  event: string;
  status?: string;
  sku?: string;
  title?: string;
  ebayListingId?: string;
  sourceListingId?: string;
  source?: string;
  skus?: string[];
  failed_skus?: string[];
  quantity?: number;
  count?: number;
  error?: string;
  timestamp: string;
  [key: string]: unknown;
}

interface FilterOption {
  key: string;
  label: string;
}

interface LogsTabProps {
  onNavigateToSku?: (sku: string) => void;
}

const EVENT_LABELS: Record<string, string> = {
  draft_created: "Draft Created",
  draft_completed: "Draft Completed",
  upload: "Upload",
  restock: "Restock",
  import: "Import",
};

const FILTERS: FilterOption[] = [
  { key: "all", label: "All" },
  { key: "upload", label: "Uploads" },
  { key: "restock", label: "Restocks" },
  { key: "draft_created", label: "Drafts Created" },
  { key: "draft_completed", label: "Drafts Completed" },
  { key: "import", label: "Imports" },
];

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

export default function LogsTab({ onNavigateToSku }: LogsTabProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

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
        {FILTERS.map((f) => (
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
          const hasSku = !!entry.sku;
          return (
            <div
              key={i}
              className={`flex items-start gap-3 rounded-md px-3 py-2.5 text-sm ${
                isError ? "bg-danger/5" : "hover:bg-surface-hover"
              } ${hasSku && onNavigateToSku ? "cursor-pointer" : ""}`}
              onClick={
                hasSku && onNavigateToSku
                  ? () => onNavigateToSku(entry.sku!)
                  : undefined
              }
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
                  {EVENT_LABELS[entry.event] ?? entry.event}
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
