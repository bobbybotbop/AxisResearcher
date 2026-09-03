import { useState } from "react";
import MessageBarInput from "./MessageBarInput";
import { btnPill } from "../styles/buttonPill";
import { fetchWithProgress } from "../utils/fetchWithProgress";

function ThreeDFileFinder({ addToast }) {
  const [linkValue, setLinkValue] = useState("");
  const [photos, setPhotos] = useState([]);
  const [listingTitle, setListingTitle] = useState("");
  const [fetchingPhotos, setFetchingPhotos] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const handleSubmitLink = async (e) => {
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
      );
      setPhotos(data.photos || []);
      setListingTitle(data.listing?.title || "");
      if (data.photos?.length > 0) {
        setSelectedPhoto(data.photos[0]);
      }
    } catch (err) {
      addToast?.("error", err.message || "Failed to fetch listing photos");
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
      const res = await fetch("/api/serper-lens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: selectedPhoto }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || "Search failed");
      }
      setSearchResults(data.results || []);
      if (data.results?.length === 0) {
        addToast?.("info", "No 3D file results found for this image");
      }
    } catch (err) {
      addToast?.("error", err.message || "Serper search failed");
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
            {searchResults.map((r, i) => (
              <li
                key={r.link}
                className="flex items-start gap-3 rounded-lg border border-border-default bg-surface-muted p-3 transition-colors hover:bg-surface-hover"
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
                  <a
                    href={r.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-primary hover:underline"
                  >
                    {r.title || r.link}
                  </a>
                  <p className="truncate text-xs text-text-muted">
                    {r.source || (() => { try { return new URL(r.link).hostname; } catch { return r.link; } })()}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export default ThreeDFileFinder;
