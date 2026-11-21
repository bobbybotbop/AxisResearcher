import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  ChevronRight,
  ChevronDown,
  ChevronLeft,
  Database,
  Table2,
} from "lucide-react";

const TABLES = ["listings", "preferences", "logs", "prompts"] as const;
type TableName = (typeof TABLES)[number];

const TABLE_LABELS: Record<TableName, string> = {
  listings: "listings",
  preferences: "preferences",
  logs: "logs",
  prompts: "prompts",
};

interface DataBrowserResponse {
  table: string;
  columns: string[];
  rows: Record<string, unknown>[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
}

/** Check if a string value looks like an image URL. */
function isImageUrl(value: unknown): boolean {
  if (typeof value !== "string") return false;
  return /\.(png|jpe?g|gif|webp|svg|bmp|avif)(\?.*)?$/i.test(value) ||
    /^https?:\/\/.*(image|img|photo|picture|eps)/i.test(value);
}

/** Check if a string value looks like a JSON array of image URLs. */
function extractImageUrls(value: unknown): string[] {
  if (typeof value !== "string") return [];
  // Direct image URL
  if (isImageUrl(value)) return [value];
  // Try parsing as JSON array
  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed.filter(
        (item): item is string => typeof item === "string" && isImageUrl(item),
      );
    }
  } catch {
    // not JSON
  }
  return [];
}

/** Format a cell value for the collapsed row preview. */
function cellPreview(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") {
    return value.length > 80 ? value.slice(0, 80) + "…" : value;
  }
  return String(value);
}

/** Render a single field in the expanded detail view. */
function DetailField({ name, value }: { name: string; value: unknown }) {
  const imageUrls = extractImageUrls(value);

  if (imageUrls.length > 0) {
    return (
      <div className="flex flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          {name}
        </span>
        <div className="flex flex-wrap gap-2">
          {imageUrls.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="group"
            >
              <img
                src={url}
                alt={`${name}[${i}]`}
                className="h-24 w-24 rounded-md border border-border-default object-cover transition-transform group-hover:scale-105"
                loading="lazy"
                onError={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = "none";
                  // Show the URL as fallback text
                  const fallback = document.createElement("span");
                  fallback.className = "text-xs text-text-muted break-all";
                  fallback.textContent = url;
                  target.parentElement?.appendChild(fallback);
                }}
              />
            </a>
          ))}
        </div>
        <span className="break-all text-xs text-text-muted">
          {typeof value === "string" && value.length > 200
            ? value.slice(0, 200) + "…"
            : String(value)}
        </span>
      </div>
    );
  }

  // Long text (like raw_json or content) — render in a scrollable block
  const strValue =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const isLong = strValue.length > 200;

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
        {name}
      </span>
      {isLong ? (
        <pre className="max-h-64 overflow-auto rounded-md border border-border-default bg-surface-app p-3 text-xs text-text-secondary whitespace-pre-wrap break-all">
          {strValue}
        </pre>
      ) : (
        <span className="text-sm text-text-primary break-all">{strValue}</span>
      )}
    </div>
  );
}

export default function DataBrowser() {
  const [selectedTable, setSelectedTable] = useState<TableName>("listings");
  const [data, setData] = useState<DataBrowserResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const fetchData = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(
        `/api/data-browser/${selectedTable}?page=${page}&page_size=${pageSize}`,
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const json = (await res.json()) as DataBrowserResponse;
      setData(json);
    } catch (err) {
      setFetchError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [selectedTable, page, pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset page and expanded rows when switching tables
  useEffect(() => {
    setPage(1);
    setExpandedRows(new Set());
  }, [selectedTable]);

  function toggleRow(index: number) {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  // Pick key columns for the collapsed row display
  function keyColumns(row: Record<string, unknown>): [string, unknown][] {
    if (!data) return [];
    const preferred: Record<TableName, string[]> = {
      listings: ["sku", "title", "price", "quantity", "ebay_status"],
      preferences: ["key", "value"],
      logs: ["id", "timestamp", "event", "status"],
      prompts: ["name", "updated_at"],
    };
    const keys = preferred[selectedTable] || data.columns.slice(0, 4);
    return keys
      .filter((k) => k in row)
      .map((k) => [k, row[k]] as [string, unknown]);
  }

  return (
    <div className="flex h-full flex-col py-6 px-2">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text-primary">Data Browser</h1>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-md border border-border-default px-3 py-1.5 text-sm text-text-muted hover:text-text-primary hover:bg-surface-hover disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Left sidebar: table list */}
        <div className="flex w-48 shrink-0 flex-col gap-0.5 rounded-lg border border-border-default bg-surface-panel p-2">
          <div className="mb-2 flex items-center gap-2 px-2 py-1">
            <Database size={14} className="text-text-muted" />
            <span className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Tables
            </span>
          </div>
          {TABLES.map((table) => (
            <button
              key={table}
              onClick={() => setSelectedTable(table)}
              className={`flex items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors ${
                selectedTable === table
                  ? "bg-primary/10 font-semibold text-primary"
                  : "text-text-muted hover:bg-surface-hover hover:text-text-primary"
              }`}
            >
              <Table2 size={14} className="shrink-0" />
              {TABLE_LABELS[table]}
            </button>
          ))}
        </div>

        {/* Main area: rows */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {fetchError && (
            <div className="mb-4 rounded-md bg-danger/10 px-4 py-3 text-sm text-danger">
              {fetchError}
            </div>
          )}

          {!loading && data && data.rows.length === 0 && !fetchError && (
            <p className="py-8 text-center text-sm text-text-muted">
              No rows in {selectedTable}.
            </p>
          )}

          {data && data.rows.length > 0 && (
            <>
              <div className="flex-1 overflow-auto">
                <div className="flex flex-col gap-1">
                  {data.rows.map((row, index) => {
                    const isExpanded = expandedRows.has(index);
                    const preview = keyColumns(row);
                    return (
                      <div key={index} className="flex flex-col">
                        {/* Collapsed row */}
                        <div
                          className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2.5 text-sm hover:bg-surface-hover"
                          onClick={() => toggleRow(index)}
                        >
                          <span className="shrink-0 text-text-muted">
                            {isExpanded ? (
                              <ChevronDown size={14} />
                            ) : (
                              <ChevronRight size={14} />
                            )}
                          </span>
                          <div className="flex min-w-0 flex-1 items-center gap-4">
                            {preview.map(([key, value]) => (
                              <div
                                key={key}
                                className="min-w-0 flex items-center gap-1"
                              >
                                <span className="shrink-0 text-xs text-text-muted">
                                  {key}:
                                </span>
                                <span className="truncate text-text-primary">
                                  {cellPreview(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Expanded detail */}
                        {isExpanded && (
                          <div className="ml-9 mb-2 flex flex-col gap-3 rounded-md border border-border-default bg-surface-panel p-4">
                            {Object.entries(row).map(([key, value]) => (
                              <DetailField
                                key={key}
                                name={key}
                                value={value}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Pagination bar */}
              <div className="mt-3 flex items-center justify-between border-t border-border-default pt-3">
                <span className="text-xs text-text-muted">
                  {data.total_rows} row{data.total_rows !== 1 ? "s" : ""} · page{" "}
                  {data.page} of {data.total_pages}
                </span>
                <div className="flex items-center gap-2">
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    className="rounded-md border border-border-default bg-surface-panel px-2 py-1 text-xs text-text-primary"
                  >
                    {[10, 25, 50, 100].map((n) => (
                      <option key={n} value={n}>
                        {n} / page
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="flex items-center gap-1 rounded-md border border-border-default px-2 py-1 text-xs text-text-muted hover:bg-surface-hover hover:text-text-primary disabled:opacity-40"
                  >
                    <ChevronLeft size={12} />
                    Prev
                  </button>
                  <button
                    onClick={() =>
                      setPage((p) => Math.min(data.total_pages, p + 1))
                    }
                    disabled={page >= data.total_pages}
                    className="flex items-center gap-1 rounded-md border border-border-default px-2 py-1 text-xs text-text-muted hover:bg-surface-hover hover:text-text-primary disabled:opacity-40"
                  >
                    Next
                    <ChevronRight size={12} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
