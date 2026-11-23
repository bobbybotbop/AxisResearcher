import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, RefreshCw, Search, X } from "lucide-react";
import Lightbox from "./Lightbox";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import { formatListingDateTime } from "../utils/listingDisplay";
import { startTask, startTaskWithId, useTaskRunning } from "../utils/statusStore";
import {
  PIPELINE_IMAGE_SEARCH,
  PIPELINE_TITLE_SEARCH,
  MATCH_LABEL_CONFIRMED_IMAGE_MATCH,
  MATCH_LABEL_UNCONFIRMED_TITLE_MATCH,
} from "../constants/files3d";

interface Saved3DFile {
  id: number;
  ebay_listing_url: string;
  ebay_listing_title: string;
  source_site: string;
  source_url: string;
  match_label: string;
  pipeline: string;
  file_path: string;
  images_dir: string;
  created_at: string;
  images: string[];
}

interface Saved3DFilesResponse {
  items: Saved3DFile[];
  total: number;
  page: number;
  page_size: number;
}

const MATCH_LABEL_TEXT: Record<string, string> = {
  [MATCH_LABEL_CONFIRMED_IMAGE_MATCH]: "Confirmed image match",
  [MATCH_LABEL_UNCONFIRMED_TITLE_MATCH]: "Unconfirmed title match",
};

const PIPELINE_TEXT: Record<string, string> = {
  [PIPELINE_IMAGE_SEARCH]: "Image Search",
  [PIPELINE_TITLE_SEARCH]: "Title Search",
};

function matchLabelText(raw: string): string {
  return MATCH_LABEL_TEXT[raw] ?? raw;
}

function pipelineText(raw: string): string {
  return PIPELINE_TEXT[raw] ?? raw;
}

function imageUrl(entry: Saved3DFile, filename: string): string {
  return `/api/saved-3d-files/${entry.id}/images/${encodeURIComponent(filename)}`;
}

function MatchLabelBadge({ label }: { label: string }) {
  const confirmed = label === MATCH_LABEL_CONFIRMED_IMAGE_MATCH;
  const cls = confirmed
    ? "border-success/30 bg-success/10 text-success"
    : "border-warning/30 bg-warning/10 text-warning";
  return (
    <span
      className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}
      title={matchLabelText(label)}
    >
      {matchLabelText(label)}
    </span>
  );
}

function PipelineBadge({ pipeline }: { pipeline: string }) {
  return (
    <span
      className="shrink-0 rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
      title={pipelineText(pipeline)}
    >
      {pipelineText(pipeline)}
    </span>
  );
}

function SiteBadge({ site }: { site: string }) {
  if (!site) return null;
  return (
    <span
      className="shrink-0 rounded-full border border-border-default bg-surface-muted px-2 py-0.5 text-xs font-medium text-text-secondary"
      title={site}
    >
      {site}
    </span>
  );
}

function Badges({ entry }: { entry: Saved3DFile }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <SiteBadge site={entry.source_site} />
      <MatchLabelBadge label={entry.match_label} />
      <PipelineBadge pipeline={entry.pipeline} />
    </div>
  );
}

function SkeletonBar({ className }: { className: string }) {
  return <div className={`animate-pulse rounded bg-surface-hover ${className}`} />;
}

function CompactSaved3DFileRowSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex w-full overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm"
    >
      <SkeletonBar className="h-20 w-24 shrink-0 rounded-none" />
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-2 px-3 py-2">
        <SkeletonBar className="h-4 w-2/3" />
        <SkeletonBar className="h-3 w-1/3" />
      </div>
    </div>
  );
}

function DetailedSaved3DFileCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="flex w-full flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm md:flex-row md:items-stretch"
    >
      <div className="w-full shrink-0 border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r">
        <SkeletonBar className="aspect-square w-full rounded-none" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-3 p-4 sm:p-5">
        <SkeletonBar className="h-5 w-3/4" />
        <div className="flex gap-1.5">
          <SkeletonBar className="h-5 w-16 rounded-full" />
          <SkeletonBar className="h-5 w-24 rounded-full" />
          <SkeletonBar className="h-5 w-20 rounded-full" />
        </div>
        <SkeletonBar className="h-3 w-1/3" />
        <SkeletonBar className="h-3 w-1/2" />
      </div>
    </div>
  );
}

function Saved3DFileSkeletons({ viewMode }: { viewMode: "compact" | "detailed" }) {
  return (
    <div className="flex flex-col gap-4" role="status" aria-label="Loading saved 3D files">
      {Array.from({ length: 4 }, (_, i) =>
        viewMode === "compact" ? (
          <CompactSaved3DFileRowSkeleton key={i} />
        ) : (
          <DetailedSaved3DFileCardSkeleton key={i} />
        ),
      )}
    </div>
  );
}

function CompactSaved3DFileRow({
  entry,
  onCardClick,
}: {
  entry: Saved3DFile;
  onCardClick: (entry: Saved3DFile) => void;
}) {
  const [imageIndex, setImageIndex] = useState(0);
  const urls = entry.images.map((name) => imageUrl(entry, name));
  const safeIndex = urls.length ? imageIndex % urls.length : 0;
  const title = entry.ebay_listing_title || "No title";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onCardClick(entry)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardClick(entry);
        }
      }}
      className="flex w-full cursor-pointer overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Thumbnail */}
      <div className="relative h-20 w-24 shrink-0 bg-surface-muted">
        {urls.length > 0 ? (
          <div className="flex h-full w-full items-center justify-center">
            <img
              src={urls[safeIndex]}
              alt={title}
              className="max-h-full max-w-full object-contain"
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            No image
          </div>
        )}
        {urls.length > 1 && (
          <div className="absolute bottom-1.5 left-0 right-0 flex justify-center gap-1.5">
            {urls.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Show image ${i + 1}`}
                className={`h-1.5 w-1.5 rounded-full ring-1 ring-white ring-offset-0 transition-all ${
                  i === safeIndex ? "w-4 bg-black" : "bg-black/50 hover:bg-black/80"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  setImageIndex(i);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Content column */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-1 px-3 py-2">
        <div className="flex shrink-0 items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-1 text-base font-semibold leading-snug text-text-primary">
              {title}
            </h3>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0 text-sm text-text-muted">
              <span>{formatListingDateTime(entry.created_at)}</span>
              <span className="text-text-muted">·</span>
              <span className="whitespace-nowrap">
                {urls.length} {urls.length === 1 ? "image" : "images"}
              </span>
            </p>
          </div>
          <Badges entry={entry} />
        </div>
      </div>
    </div>
  );
}

function DetailedSaved3DFileCard({
  entry,
  onCardClick,
}: {
  entry: Saved3DFile;
  onCardClick: (entry: Saved3DFile) => void;
}) {
  const [imageIndex, setImageIndex] = useState(0);
  const urls = entry.images.map((name) => imageUrl(entry, name));
  const safeIndex = urls.length ? imageIndex % urls.length : 0;
  const title = entry.ebay_listing_title || "No title";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onCardClick(entry)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardClick(entry);
        }
      }}
      className="flex w-full cursor-pointer flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md md:flex-row md:items-stretch"
    >
      {/* Image column */}
      <div className="flex w-full shrink-0 flex-col border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r">
        <div className="relative w-full">
          <div className="aspect-square w-full bg-surface-muted">
            {urls.length > 0 ? (
              <div className="flex h-full w-full items-center justify-center">
                <img
                  src={urls[safeIndex]}
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
          {urls.length > 1 && (
            <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5">
              {urls.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  aria-label={`Show image ${i + 1}`}
                  className={`h-1.5 w-1.5 rounded-full ring-1 ring-white ring-offset-0 transition-all ${
                    i === safeIndex ? "w-4 bg-black" : "bg-black/50 hover:bg-black/80"
                  }`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setImageIndex(i);
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Content column */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 p-4 sm:p-5">
        <h3 className="line-clamp-2 text-lg font-bold leading-tight text-text-primary sm:text-xl">
          {title}
        </h3>
        <Badges entry={entry} />
        <p className="flex flex-wrap items-center gap-x-2 gap-y-0 text-sm text-text-muted">
          <span>{formatListingDateTime(entry.created_at)}</span>
          <span className="text-text-muted">·</span>
          <span className="whitespace-nowrap">
            {urls.length} {urls.length === 1 ? "image" : "images"}
          </span>
        </p>
        {entry.source_url && (
          <a
            href={entry.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="truncate text-sm font-medium text-primary underline hover:no-underline"
            onClick={(e) => e.stopPropagation()}
          >
            View on {entry.source_site || "source site"} →
          </a>
        )}
      </div>
    </div>
  );
}

function MetaRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="shrink-0 text-sm text-text-muted">{label}</span>
      <span
        className={`truncate text-right text-sm font-medium text-text-primary ${mono ? "font-mono text-xs" : ""}`}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

function Saved3DFileDetailModal({
  entry,
  onClose,
  onDeleted,
}: {
  entry: Saved3DFile;
  onClose: () => void;
  onDeleted: (id: number) => void;
}) {
  const [heroIndex, setHeroIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteTaskId, setDeleteTaskId] = useState<number | null>(null);
  const deletePending = useTaskRunning(deleteTaskId);

  const urls = entry.images.map((name) => imageUrl(entry, name));
  const safeHero = urls.length ? heroIndex % urls.length : 0;
  const title = entry.ebay_listing_title || "No title";

  const handleDelete = async () => {
    setDeleteError(null);
    const { id, handle: task } = startTaskWithId(`Deleting saved 3D file #${entry.id}`);
    setDeleteTaskId(id);
    try {
      const res = await fetch(`/api/saved-3d-files/${entry.id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      task.succeed("Saved 3D file deleted");
      onDeleted(entry.id);
      onClose();
    } catch (err) {
      const message = (err as Error).message;
      task.fail(message);
      setDeleteError(message);
      setConfirmDelete(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-surface-panel shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 border-b border-border-default px-5 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="rounded-md bg-surface-muted px-2.5 py-1 font-mono text-xs font-semibold text-text-primary">
              #{entry.id}
            </span>
            <Badges entry={entry} />
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-none bg-surface-muted text-xl text-text-muted transition-all hover:rotate-90 hover:bg-surface-hover hover:text-text-primary"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <div className="grid gap-6 p-5 md:grid-cols-2">
            {/* Gallery */}
            <div className="flex min-w-0 flex-col gap-3">
              <button
                type="button"
                className="relative aspect-square w-full cursor-zoom-in overflow-hidden rounded-lg border border-border-default bg-surface-muted"
                onClick={() => urls.length && setLightboxOpen(true)}
                aria-label="Open image viewer"
              >
                {urls.length > 0 ? (
                  <img
                    src={urls[safeHero]}
                    alt={title}
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <span className="flex h-full items-center justify-center text-sm text-text-muted">
                    No images
                  </span>
                )}
                {urls.length > 0 && (
                  <span className="absolute bottom-2 right-2 rounded-md bg-black/55 px-2 py-0.5 text-xs font-medium text-white">
                    {safeHero + 1} / {urls.length}
                  </span>
                )}
              </button>
              {urls.length > 1 && (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {urls.map((url, i) => (
                    <button
                      key={i}
                      type="button"
                      aria-label={`Show image ${i + 1}`}
                      className={`h-16 w-16 shrink-0 overflow-hidden rounded-md border bg-surface-muted transition-shadow ${
                        i === safeHero
                          ? "border-primary ring-2 ring-primary/40"
                          : "border-border-default hover:ring-2 hover:ring-primary/25"
                      }`}
                      onClick={() => setHeroIndex(i)}
                    >
                      <img src={url} alt="" className="h-full w-full object-cover" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Metadata + actions */}
            <div className="flex min-w-0 flex-col gap-4">
              <h2 className="text-xl font-bold leading-snug text-text-primary md:text-2xl">
                {title}
              </h2>

              <div className="flex flex-wrap gap-2">
                <a
                  href={`/api/saved-3d-files/${entry.id}/download`}
                  download
                  className={`inline-flex items-center justify-center no-underline ${btnPill}`}
                >
                  Download 3D file
                </a>
                {!confirmDelete ? (
                  <button
                    type="button"
                    className={`${btnPill} border-danger/30 text-danger hover:bg-danger/10`}
                    onClick={() => setConfirmDelete(true)}
                  >
                    Delete
                  </button>
                ) : (
                  <>
                    <button
                      type="button"
                      disabled={deletePending}
                      className="rounded-full border border-danger/30 bg-danger px-6 py-2.5 text-base font-light leading-snug tracking-tight text-white transition-colors hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                      onClick={handleDelete}
                    >
                      {deletePending ? "Deleting..." : "Confirm delete"}
                    </button>
                    <button
                      type="button"
                      disabled={deletePending}
                      className={btnPill}
                      onClick={() => setConfirmDelete(false)}
                    >
                      Cancel
                    </button>
                  </>
                )}
              </div>
              {deleteError && (
                <div className="rounded-md bg-danger/10 px-4 py-3 text-sm text-danger">
                  {deleteError}
                </div>
              )}

              <div className="rounded-xl border border-border-default bg-surface-muted p-4">
                <h3 className="mb-3 border-b border-border-default pb-2 text-base font-semibold text-text-primary">
                  Details
                </h3>
                <MetaRow label="Saved" value={formatListingDateTime(entry.created_at)} />
                <MetaRow label="Source site" value={entry.source_site} />
                <MetaRow label="Match label" value={matchLabelText(entry.match_label)} />
                <MetaRow label="Pipeline" value={pipelineText(entry.pipeline)} />
                <MetaRow label="3D file" value={entry.file_path} mono />
                <div className="mt-3 flex flex-col gap-2 border-t border-border-default pt-3">
                  {entry.source_url && (
                    <a
                      href={entry.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-sm font-medium text-primary underline hover:no-underline"
                    >
                      View on {entry.source_site || "source site"} →
                    </a>
                  )}
                  {entry.ebay_listing_url && (
                    <a
                      href={entry.ebay_listing_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-sm font-medium text-primary underline hover:no-underline"
                    >
                      View eBay listing →
                    </a>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {lightboxOpen && urls.length > 0 && (
        <Lightbox
          photos={urls}
          currentIndex={safeHero}
          onClose={() => setLightboxOpen(false)}
          onNavigate={(direction) =>
            setHeroIndex((prev) =>
              direction === "next"
                ? (prev + 1) % urls.length
                : (prev - 1 + urls.length) % urls.length,
            )
          }
        />
      )}
    </div>
  );
}

export default function Saved3DFiles() {
  const [data, setData] = useState<Saved3DFilesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"compact" | "detailed">(() => {
    try {
      return localStorage.getItem("axisSaved3DFilesViewMode") === "detailed"
        ? "detailed"
        : "compact";
    } catch {
      return "compact";
    }
  });
  const [selected, setSelected] = useState<Saved3DFile | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    // Report the load through the Status Store (ADR 0002); the skeleton cards
    // stay gated on the local loading flag as their local trigger.
    const task = startTask("Load saved 3D files");
    try {
      const res = await fetch(`/api/saved-3d-files?page=${page}&page_size=${pageSize}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      setData((await res.json()) as Saved3DFilesResponse);
      task.succeed();
    } catch (err) {
      const message = (err as Error).message;
      setFetchError(message);
      task.fail(message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleViewModeChange = (mode: "compact" | "detailed") => {
    setViewMode(mode);
    try {
      localStorage.setItem("axisSaved3DFilesViewMode", mode);
    } catch {
      // ignore
    }
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const items = data?.items ?? [];
    if (!q) return items;
    return items.filter(
      (entry) =>
        (entry.ebay_listing_title || "").toLowerCase().includes(q) ||
        (entry.source_site || "").toLowerCase().includes(q),
    );
  }, [data, search]);

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / pageSize));

  const handleDeleted = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="flex h-full flex-col py-6">
      {/* Toolbar */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search
            size={16}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or source site..."
            className="w-full rounded-lg border border-border-default bg-surface-panel py-2 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-border-default/40"
          />
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-border-default bg-surface-panel p-1">
          <button
            type="button"
            onClick={() => handleViewModeChange("compact")}
            className={`rounded-md px-3 py-1 text-sm transition-colors ${
              viewMode === "compact"
                ? "bg-primary/10 font-semibold text-primary"
                : "text-text-muted hover:text-text-primary"
            }`}
          >
            Compact
          </button>
          <button
            type="button"
            onClick={() => handleViewModeChange("detailed")}
            className={`rounded-md px-3 py-1 text-sm transition-colors ${
              viewMode === "detailed"
                ? "bg-primary/10 font-semibold text-primary"
                : "text-text-muted hover:text-text-primary"
            }`}
          >
            Detailed
          </button>
        </div>
        <button
          type="button"
          onClick={fetchData}
          disabled={loading}
          className={`flex items-center gap-1.5 ${btnPillSm}`}
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {fetchError && (
        <div className="mb-4 rounded-md bg-danger/10 px-4 py-3 text-sm text-danger">
          {fetchError}
        </div>
      )}

      {/* List */}
      {loading && !data ? (
        <Saved3DFileSkeletons viewMode={viewMode} />
      ) : (data?.items.length ?? 0) === 0 ? (
        <div className="rounded-xl border border-border-default bg-surface-muted p-8 text-center">
          <p className="text-text-muted">
            No saved 3D files yet. Download one via the 3D File Finder.
          </p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-border-default bg-surface-muted p-8 text-center">
          <p className="text-text-muted">No saved 3D files match your search.</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-4">
            {filtered.map((entry) =>
              viewMode === "compact" ? (
                <CompactSaved3DFileRow
                  key={entry.id}
                  entry={entry}
                  onCardClick={setSelected}
                />
              ) : (
                <DetailedSaved3DFileCard
                  key={entry.id}
                  entry={entry}
                  onCardClick={setSelected}
                />
              ),
            )}
          </div>

          {/* Pagination */}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Previous page"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="min-w-28 text-center text-sm text-text-muted">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                aria-label="Next page"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronRight size={16} />
              </button>
            </div>

            <div className="flex items-center gap-2 text-sm text-text-muted">
              <span>Per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="rounded-md border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-border-default/40"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>
          </div>
        </>
      )}

      {selected && (
        <Saved3DFileDetailModal
          entry={selected}
          onClose={() => setSelected(null)}
          onDeleted={handleDeleted}
        />
      )}
    </div>
  );
}
