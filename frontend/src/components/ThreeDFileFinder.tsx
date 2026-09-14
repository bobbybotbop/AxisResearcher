import { useState } from "react";
import MessageBarInput from "./MessageBarInput";
import { btnPill } from "../styles/buttonPill";
import { fetchWithProgress } from "../utils/fetchWithProgress";

interface SearchResult {
  site_type?: string;
  link: string;
  title?: string;
  thumbnail?: string;
  source?: string;
}

interface ThreeDFileFinderProps {
  addToast?: (type: string, message: string) => void;
}

function ThreeDFileFinder({ addToast }: ThreeDFileFinderProps) {
  const [linkValue, setLinkValue] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);
  const [listingTitle, setListingTitle] = useState("");
  const [fetchingPhotos, setFetchingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSubmitLink = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = linkValue.trim();
    if (!trimmed) {
      addToast?.("error", "Please enter an eBay listing ID or URL");
      return;
    }

    setFetchingPhotos(true);
    setPhotos([]);
    setListingTitle("");
    setSelectedPhoto(null);
    setSearchResults([]);

    try {
      const data = await fetchWithProgress(
        `/api/photos/${encodeURIComponent(trimmed)}?classify=false`,
        {},
        () => {},
      ) as { photos?: string[]; listing?: { title?: string } };
      setPhotos(data.photos || []);
      setListingTitle(data.listing?.title || "");
      if (data.photos && data.photos.length > 0) {
        setSelectedPhoto(data.photos[0]);
      }
    } catch (err) {
      addToast?.("error", (err as Error).message || "Failed to fetch listing photos");
    } finally {
      setFetchingPhotos(false);
      setLinkValue("");
    }
  };

  const handleSearch = async () => {
    if (!selectedPhoto) return;

    setSearching(true);
    setSearchResults([]);

    try {
      const res = await fetch("/api/serp-lens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: selectedPhoto }),
      });
      const data = await res.json() as { error?: string; results?: SearchResult[] };
      if (!res.ok || data.error) {
        throw new Error(data.error || "Search failed");
      }
      setSearchResults(data.results || []);
      if (!data.results || data.results.length === 0) {
        addToast?.("info", "No 3D file results found for this image");
      }
    } catch (err) {
      addToast?.("error", (err as Error).message || "Serper search failed");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="mb-1 text-lg font-semibold text-text-primary">
          3D File Finder
        </h3>
        <p className="text-sm text-text-muted">
          Paste an eBay listing link to find the original 3D print file.
        </p>
      </div>

      <form onSubmit={handleSubmitLink} className="flex items-end gap-3">
        <div className="flex-1">
          <MessageBarInput
            value={linkValue}
            onChange={setLinkValue}
            placeholder="Paste eBay listing URL or item ID..."
            disabled={fetchingPhotos}
            loading={fetchingPhotos}
            aria-label="eBay listing URL"
            fullWidth
          />
        </div>
      </form>

      {photos.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-text-primary">
              {listingTitle && (
                <span className="text-text-muted">{listingTitle} &ndash; </span>
              )}
              Select a photo to search ({photos.length} found)
            </p>
            <button
              type="button"
              className={btnPill}
              onClick={handleSearch}
              disabled={!selectedPhoto || searching}
            >
              {searching ? "Searching..." : "Find 3D File"}
            </button>
          </div>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8">
            {photos.map((url, i) => (
              <button
                key={url}
                type="button"
                onClick={() => setSelectedPhoto(url)}
                className={`aspect-square overflow-hidden rounded-lg border-2 transition-all ${
                  selectedPhoto === url
                    ? "border-primary ring-2 ring-primary/30"
                    : "border-border-default hover:border-primary/50"
                }`}
              >
                <img
                  src={url}
                  alt={`Listing photo ${i + 1}`}
                  className="h-full w-full object-cover"
                />
              </button>
            ))}
          </div>
        </div>
      )}

      {searchResults.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-text-primary">
            Results ({searchResults.length})
          </p>
          <ol className="flex flex-col gap-2">
            {searchResults.map((r, i) => {
              const isWhitelisted = r.site_type === "whitelisted";
              const isBlacklisted = r.site_type === "blacklisted";
              const hostname = (() => {
                try { return new URL(r.link).hostname; } catch { return r.link; }
              })();
              return (
                <li
                  key={r.link}
                  className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                    isWhitelisted
                      ? "border-green-500/40 bg-green-500/5 hover:bg-green-500/10"
                      : isBlacklisted
                        ? "border-red-500/30 bg-red-500/5 hover:bg-red-500/10 opacity-60"
                        : "border-border-default bg-surface-muted hover:bg-surface-hover"
                  }`}
                >
                  <span className="mt-0.5 shrink-0 text-sm font-bold text-text-muted">
                    {i + 1}.
                  </span>
                  {r.thumbnail && (
                    <img
                      src={r.thumbnail}
                      alt=""
                      className="h-10 w-10 shrink-0 rounded object-cover"
                    />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <a
                        href={r.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-primary hover:underline"
                      >
                        {r.title || r.link}
                      </a>
                      {isWhitelisted && (
                        <span className="shrink-0 rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-400">
                          3D site
                        </span>
                      )}
                      {isBlacklisted && (
                        <span className="shrink-0 rounded-full bg-red-500/15 px-2 py-0.5 text-xs font-medium text-red-400">
                          marketplace
                        </span>
                      )}
                    </div>
                    <p className="truncate text-xs text-text-muted">
                      {r.source || hostname}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </div>
  );
}

export default ThreeDFileFinder;
