import { useState } from "react";
import MessageBarInput from "./MessageBarInput";
import { btnPill, btnPillSm } from "../styles/buttonPill";
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
  const [downloadingLink, setDownloadingLink] = useState<string | null>(null);

  const handleDownload = async (link: string) => {
    setDownloadingLink(link);
    try {
      const res = await fetch("/api/download-3d-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link }),
      });
      if (!res.ok) {
        let errMsg = `Download failed (${res.status})`;
        try {
          const err = await res.json() as { error?: string };
          if (err.error) errMsg = err.error;
        } catch { /* ignore parse failure */ }
        throw new Error(errMsg);
      }
      const disposition = res.headers.get("Content-Disposition") || "";
      const nameMatch = disposition.match(/filename="?([^"]+)"?/);
      const filename = nameMatch ? nameMatch[1] : "download.zip";
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      addToast?.("error", (err as Error).message || "Download failed");
    } finally {
      setDownloadingLink(null);
    }
  };

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
      const filtered = (data.results || []).filter(r => r.site_type === "whitelisted");
      setSearchResults(filtered);
      if (filtered.length === 0) {
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
              const hostname = (() => {
                try { return new URL(r.link).hostname; } catch { return r.link; }
              })();
              const canDownload =
                /thingiverse\.com\/thing[:/]\d+/.test(r.link) ||
                /printables\.com\/model\/\d+/.test(r.link);
              const isDownloading = downloadingLink === r.link;
              const isAnyDownloading = downloadingLink !== null;

              return (
                <li
                  key={r.link}
                  className="flex items-center gap-3 rounded-lg border p-3 transition-colors border-green-500/40 bg-green-500/5"
                >
                  <span className="shrink-0 text-sm font-bold text-text-muted w-5 text-right">
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
                      <span className="shrink-0 rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-400">
                        3D site
                      </span>
                    </div>
                    <p className="truncate text-xs text-text-muted">
                      {r.source || hostname}
                    </p>
                  </div>
                  {canDownload && (
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={() => handleDownload(r.link)}
                      disabled={isAnyDownloading}
                    >
                      {isDownloading ? "Downloading..." : "Download"}
                    </button>
                  )}
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
