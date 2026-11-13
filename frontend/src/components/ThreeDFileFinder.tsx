import { useState } from "react";
import JSZip from "jszip";
import MessageBarInput from "./MessageBarInput";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import { DOWNLOAD_MODE_FILES, DOWNLOAD_MODE_FULL_ZIP, DOWNLOAD_MODE_SINGLE_FILE, threeDSiteKeyFromLink, type DownloadMode, type ThreeDSiteStatus } from "../constants/files3d";

interface SearchResult {
  site_type?: string;
  link: string;
  title?: string;
  thumbnail?: string;
  source?: string;
}

// Minimal File System Access API surface (Chromium-only; absent elsewhere → fallback downloads)
interface FsWritable {
  write(data: Blob): Promise<void>;
  close(): Promise<void>;
}
interface FsDirectoryHandle {
  getDirectoryHandle(name: string, opts: { create: boolean }): Promise<FsDirectoryHandle>;
  getFileHandle(name: string, opts: { create: boolean }): Promise<{ createWritable(): Promise<FsWritable> }>;
}
interface WindowWithDirPicker {
  showDirectoryPicker?: () => Promise<FsDirectoryHandle>;
}

interface UnzippedEntry {
  path: string[]; // sanitized path segments, filename last
  data: Blob;
}

// Unzip a blob into flat entries; non-zip blobs (e.g. MakerWorld .3mf) become a single entry
const unzipBlob = async (blob: Blob, filename: string): Promise<UnzippedEntry[]> => {
  let zip: JSZip;
  try {
    zip = await JSZip.loadAsync(blob);
  } catch {
    return [{ path: [filename], data: blob }];
  }
  const entries: UnzippedEntry[] = [];
  for (const [name, entry] of Object.entries(zip.files)) {
    if (entry.dir) continue;
    // strip empty/dangerous segments so zip entries can't escape the target folder
    const parts = name.split("/").filter((s) => s !== "" && s !== "." && s !== "..");
    if (parts.length === 0) continue;
    entries.push({ path: parts, data: await entry.async("blob") });
  }
  if (entries.length === 0) throw new Error("Zip archive contains no files");
  return entries;
};

// Write entries into a user-picked folder preserving zip structure. Returns null if the user cancelled.
const saveEntriesToFolder = async (entries: UnzippedEntry[]): Promise<boolean | null> => {
  const picker = (window as unknown as WindowWithDirPicker).showDirectoryPicker;
  if (!picker) return false;
  let root: FsDirectoryHandle;
  try {
    root = await picker();
  } catch (err) {
    if ((err as Error).name === "AbortError") return null; // user cancelled the picker
    throw err;
  }
  for (const { path, data } of entries) {
    let dir = root;
    for (const segment of path.slice(0, -1)) {
      dir = await dir.getDirectoryHandle(segment, { create: true });
    }
    const fileHandle = await dir.getFileHandle(path[path.length - 1], { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(data);
    await writable.close();
  }
  return true;
};

// Fallback for browsers without the File System Access API: one download per file
const downloadEntriesIndividually = (entries: UnzippedEntry[]): void => {
  for (const { path, data } of entries) {
    const url = URL.createObjectURL(data);
    const a = document.createElement("a");
    a.href = url;
    a.download = path.join("__"); // flatten: browsers sanitize "/" in the download attribute
    a.click();
    URL.revokeObjectURL(url);
  }
};

interface ThreeDFileFinderProps {
  addToast?: (type: string, message: string) => void;
  fileDownloadDelay?: number;
  siteStatus?: ThreeDSiteStatus | null;
  enabledSites?: string[];
}

function ThreeDFileFinder({ addToast, fileDownloadDelay = 0, siteStatus = null, enabledSites }: ThreeDFileFinderProps) {
  // Step 1 — Fetch eBay Photos
  const [step1Link, setStep1Link] = useState("");
  const [step1Photos, setStep1Photos] = useState<string[]>([]);
  const [step1Title, setStep1Title] = useState("");
  const [step1Loading, setStep1Loading] = useState(false);
  const [step1Selected, setStep1Selected] = useState<string | null>(null);

  // Step 2 — Reverse Image Search
  const [step2ImageUrl, setStep2ImageUrl] = useState("");
  const [step2Results, setStep2Results] = useState<SearchResult[]>([]);
  const [step2Loading, setStep2Loading] = useState(false);

  // Step 3 — Download 3D File
  const [step3Url, setStep3Url] = useState("");
  const [step3LoadingMode, setStep3LoadingMode] = useState<DownloadMode | null>(null);
  const [step3Result, setStep3Result] = useState<{ filename: string; bytes: number; fileCount?: number } | null>(null);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // True when a result link can be forwarded to Step 3
  const canForwardToStep3 = (link: string) =>
    /thingiverse\.com\/thing[:/]\d+/.test(link) ||
    /printables\.com\/model\/\d+/.test(link) ||
    /makerworld\.com\/[^/]+\/models\/\d+/.test(link) ||
    /cults3d\.com\/[^/]+\/3d-model\/[^/]+\/[^/?#]+/.test(link);

  // True when step3Url is a supported downloadable pattern
  const step3Supported = canForwardToStep3(step3Url.trim());

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = step1Link.trim();
    if (!trimmed) {
      addToast?.("error", "Please enter an eBay listing ID or URL");
      return;
    }
    setStep1Loading(true);
    setStep1Photos([]);
    setStep1Title("");
    setStep1Selected(null);
    try {
      const res = await fetch(`/api/photos/${encodeURIComponent(trimmed)}?classify=false`);
      const data = await res.json() as {
        photos?: string[];
        listing?: { title?: string };
        error?: string;
      };
      if (!res.ok || data.error) throw new Error(data.error || "Failed to fetch photos");
      const photos = data.photos || [];
      setStep1Photos(photos);
      setStep1Title(data.listing?.title || "");
      if (photos.length > 0) setStep1Selected(photos[0]);
    } catch (err) {
      addToast?.("error", (err as Error).message || "Failed to fetch listing photos");
    } finally {
      setStep1Loading(false);
      setStep1Link("");
    }
  };

  const handleStep2Search = async () => {
    const url = step2ImageUrl.trim();
    if (!url) return;
    setStep2Loading(true);
    setStep2Results([]);
    try {
      const res = await fetch("/api/serp-lens", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_url: url, enabled_sites: enabledSites }),
      });
      const data = await res.json() as { error?: string; results?: SearchResult[] };
      if (!res.ok || data.error) throw new Error(data.error || "Search failed");
      // Skip results from 3D sites whose scraper failed the operational test
      const whitelisted = (data.results || []).filter(r => r.site_type === "whitelisted");
      const skippedSites = new Set<string>();
      const filtered = whitelisted.filter(r => {
        const key = threeDSiteKeyFromLink(r.link);
        if (key && siteStatus?.[key] && !siteStatus[key].ok) {
          skippedSites.add(key);
          return false;
        }
        return true;
      });
      setStep2Results(filtered);
      if (skippedSites.size > 0) {
        addToast?.("info", `Skipped results from ${[...skippedSites].join(", ")} — site failed its operational test (see Settings > 3D File Sites)`);
      }
      if (filtered.length === 0 && skippedSites.size === 0) addToast?.("info", "No 3D file results found for this image");
    } catch (err) {
      addToast?.("error", (err as Error).message || "Search failed");
    } finally {
      setStep2Loading(false);
    }
  };

  const handleStep3Download = async (mode: DownloadMode) => {
    const link = step3Url.trim();
    if (!link || !step3Supported) return;
    setStep3LoadingMode(mode);
    setStep3Result(null);
    setStep3Error(null);
    try {
      // "files" mode reuses the full-zip response; unzipping happens client-side
      const wireMode = mode === DOWNLOAD_MODE_FILES ? DOWNLOAD_MODE_FULL_ZIP : mode;
      const res = await fetch("/api/download-3d-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link, file_download_delay: fileDownloadDelay, mode: wireMode }),
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
      const filename = nameMatch ? nameMatch[1] : (mode === DOWNLOAD_MODE_SINGLE_FILE ? "download.3mf" : "download.zip");
      const blob = await res.blob();
      if (mode === DOWNLOAD_MODE_FILES) {
        const entries = await unzipBlob(blob, filename);
        const savedToFolder = await saveEntriesToFolder(entries);
        if (savedToFolder === null) return; // user cancelled the folder picker
        if (!savedToFolder) {
          downloadEntriesIndividually(entries);
          addToast?.("info", `Downloading ${entries.length} files individually — browser may ask to allow multiple downloads`);
        }
        setStep3Result({ filename: filename.replace(/\.zip$/i, ""), bytes: blob.size, fileCount: entries.length });
        return;
      }
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(downloadUrl);
      setStep3Result({ filename, bytes: blob.size });
    } catch (err) {
      setStep3Error((err as Error).message || "Download failed");
    } finally {
      setStep3LoadingMode(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="mb-1 text-lg font-semibold text-text-primary">3D File Finder</h3>
        <p className="text-sm text-text-muted">
          Test each step independently or run the full pipeline top to bottom.
        </p>
      </div>
      {/* Step 1 — Fetch eBay Photos */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 1 — Fetch eBay Photos</p>
        <form onSubmit={handleStep1Submit} className="flex">
          <div className="flex-1">
            <MessageBarInput
              value={step1Link}
              onChange={setStep1Link}
              placeholder="Paste eBay listing URL or item ID..."
              disabled={step1Loading}
              loading={step1Loading}
              aria-label="eBay listing URL"
              fullWidth
            />
          </div>
        </form>
        {step1Photos.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-text-muted">
              {step1Title && <span>{step1Title} — </span>}
              {step1Photos.length} photo{step1Photos.length !== 1 ? "s" : ""} found
            </p>
            <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8">
              {step1Photos.map((url, i) => (
                <button
                  key={`${i}-${url}`}
                  type="button"
                  aria-pressed={step1Selected === url}
                  onClick={() => setStep1Selected(url)}
                  className={`aspect-square overflow-hidden rounded-lg border-2 transition-colors ${
                    step1Selected === url
                      ? "border-primary ring-2 ring-primary/30"
                      : "border-border-default hover:border-primary/50"
                  }`}
                >
                  <img src={url} alt={`Photo ${i + 1}`} className="h-full w-full object-cover" />
                </button>
              ))}
            </div>
            {step1Selected && (
              <div className="flex justify-end">
                <button
                  type="button"
                  className={btnPillSm}
                  onClick={() => { setStep2ImageUrl(step1Selected!); setStep2Results([]); }}
                >
                  Use photo in Step 2 →
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      {/* Step 2 — Reverse Image Search */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 2 — Reverse Image Search</p>
        <form
          onSubmit={(e) => { e.preventDefault(); handleStep2Search(); }}
          className="flex items-center gap-3"
        >
          <div className="flex-1">
            <MessageBarInput
              value={step2ImageUrl}
              onChange={setStep2ImageUrl}
              placeholder="Paste image URL..."
              disabled={step2Loading}
              loading={step2Loading}
              aria-label="Image URL"
              fullWidth
            />
          </div>
          {step2ImageUrl && (
            <img
              src={step2ImageUrl}
              alt=""
              style={{ display: "none" }}
              className="h-8 w-8 shrink-0 rounded object-cover"
              onLoad={(e) => { (e.target as HTMLImageElement).style.display = ""; }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          )}
          <button
            type="button"
            className={btnPill}
            onClick={handleStep2Search}
            disabled={!step2ImageUrl.trim() || step2Loading}
          >
            {step2Loading ? "Searching..." : "Search"}
          </button>
        </form>
        {step2Results.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs text-text-muted">Results ({step2Results.length})</p>
            <ol className="flex flex-col gap-2">
              {step2Results.map((r, i) => {
                const hostname = (() => {
                  try { return new URL(r.link).hostname; } catch { return r.link; }
                })();
                return (
                  <li
                    key={r.link}
                    className="flex items-center gap-3 rounded-lg border border-green-500/40 bg-green-500/5 p-3"
                  >
                    <span className="w-5 shrink-0 text-right text-sm font-bold text-text-muted">
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
                      <p className="truncate text-xs text-text-muted">{r.source || hostname}</p>
                    </div>
                    {canForwardToStep3(r.link) && (
                      <button
                        type="button"
                        aria-label={`Use in Step 3: ${r.title || hostname}`}
                        className={btnPillSm}
                        onClick={() => {
                          setStep3Url(r.link);
                          setStep3Result(null);
                          setStep3Error(null);
                        }}
                      >
                        Use →
                      </button>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        )}
      </div>
      {/* Step 3 — Download 3D File */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 3 — Download 3D File</p>
        <form
          onSubmit={(e) => { e.preventDefault(); handleStep3Download(DOWNLOAD_MODE_FULL_ZIP); }}
          className="flex items-center gap-3"
        >
          <div className="flex-1">
            <MessageBarInput
              value={step3Url}
              onChange={(val) => {
                setStep3Url(val);
                setStep3Result(null);
                setStep3Error(null);
              }}
              placeholder="Paste printables.com, thingiverse.com, makerworld.com, or cults3d.com URL..."
              disabled={step3LoadingMode !== null}
              loading={step3LoadingMode !== null}
              aria-label="3D site URL"
              fullWidth
            />
          </div>
          <button
            type="button"
            className={btnPill}
            onClick={() => handleStep3Download(DOWNLOAD_MODE_FULL_ZIP)}
            disabled={!step3Supported || step3LoadingMode !== null}
          >
            {step3LoadingMode === DOWNLOAD_MODE_FULL_ZIP ? "Downloading..." : "Download Full Zip"}
          </button>
          <button
            type="button"
            className={btnPill}
            onClick={() => handleStep3Download(DOWNLOAD_MODE_SINGLE_FILE)}
            disabled={!step3Supported || step3LoadingMode !== null}
          >
            {step3LoadingMode === DOWNLOAD_MODE_SINGLE_FILE ? "Downloading..." : "Download Single File"}
          </button>
          <button
            type="button"
            className={btnPill}
            onClick={() => handleStep3Download(DOWNLOAD_MODE_FILES)}
            disabled={!step3Supported || step3LoadingMode !== null}
          >
            {step3LoadingMode === DOWNLOAD_MODE_FILES ? "Downloading..." : "Download Files"}
          </button>
        </form>
        <p className="text-xs">
          {step3Url.trim() && !step3Supported ? (
            <span className="text-amber-400">Unsupported site</span>
          ) : (
            <span className="text-text-muted">Supported: printables.com, thingiverse.com, makerworld.com, cults3d.com (free only)</span>
          )}
        </p>
        {step3Result && (
          <p className="text-sm text-green-400">
            Downloaded: {step3Result.filename}{step3Result.fileCount !== undefined ? ` (${step3Result.fileCount} file${step3Result.fileCount !== 1 ? "s" : ""} unzipped)` : ""} ({formatBytes(step3Result.bytes)})
          </p>
        )}
        {step3Error && (
          <p className="text-sm text-red-400">{step3Error}</p>
        )}
      </div>
    </div>
  );
}

export default ThreeDFileFinder;
