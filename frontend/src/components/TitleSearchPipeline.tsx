import { useState } from "react";
import MessageBarInput from "./MessageBarInput";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import { threeDSiteKeyFromLink, type ThreeDSiteStatus } from "../constants/files3d";

interface TextSearchResult {
  title: string;
  link: string;
  snippet: string;
  site_type: string;
  priority_rank: number | null;
}

// Step 3 match label: pHash image comparison lands in ticket 07 — until then
// every scraped link is an unconfirmed title match.
type MatchLabel = "checking" | "confirmed" | "unconfirmed";

const DEFAULT_MAX_RESULTS = 35;
const DEFAULT_OPTIMIZE_PROMPT = "";

interface TitleSearchPipelineProps {
  addToast?: (type: string, message: string) => void;
  enabledSites?: string[];
  sitePriority?: string[];
  siteStatus?: ThreeDSiteStatus | null;
  textModel?: string;
  onUseLink?: (link: string) => void;
}

function TitleSearchPipeline({
  addToast,
  enabledSites,
  sitePriority,
  siteStatus = null,
  textModel,
  onUseLink,
}: TitleSearchPipelineProps) {
  const [open, setOpen] = useState(true);

  // Step 1 — Fetch eBay title + photos
  const [step1Link, setStep1Link] = useState("");
  const [step1Loading, setStep1Loading] = useState(false);
  const [originalTitle, setOriginalTitle] = useState("");
  const [photos, setPhotos] = useState<string[]>([]);

  // Step 2 — Optimize title + text search
  const [optimizedTitle, setOptimizedTitle] = useState("");
  const [optimizing, setOptimizing] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [promptTemplate, setPromptTemplate] = useState(DEFAULT_OPTIMIZE_PROMPT);
  const [defaultPrompt, setDefaultPrompt] = useState<string | null>(null);
  const [maxResults, setMaxResults] = useState(DEFAULT_MAX_RESULTS);
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<TextSearchResult[]>([]);

  // Step 3 — Top-priority link image confirmation
  const [topLink, setTopLink] = useState<TextSearchResult | null>(null);
  const [siteImages, setSiteImages] = useState<string[]>([]);
  const [matchLabel, setMatchLabel] = useState<MatchLabel | null>(null);

  const searchQuery = () => {
    const base = optimizedTitle.trim();
    if (!base) return "";
    return base.endsWith(" 3d file") ? base : `${base} 3d file`;
  };

  const handleStep1Submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = step1Link.trim();
    if (!trimmed) {
      addToast?.("error", "Please enter an eBay listing ID or URL");
      return;
    }
    setStep1Loading(true);
    setOriginalTitle("");
    setPhotos([]);
    setOptimizedTitle("");
    setResults([]);
    setTopLink(null);
    setSiteImages([]);
    setMatchLabel(null);
    try {
      const res = await fetch(`/api/photos/${encodeURIComponent(trimmed)}?classify=false`);
      const data = (await res.json()) as {
        photos?: string[];
        listing?: { title?: string };
        error?: string;
      };
      if (!res.ok || data.error) throw new Error(data.error || "Failed to fetch listing");
      const fetchedPhotos = data.photos || [];
      setPhotos(fetchedPhotos);
      const title = data.listing?.title || "";
      setOriginalTitle(title);
      if (!title) addToast?.("info", "Listing fetched but no title found");
    } catch (err) {
      addToast?.("error", (err as Error).message || "Failed to fetch listing");
    } finally {
      setStep1Loading(false);
    }
  };

  const loadDefaultPrompt = async () => {
    if (defaultPrompt !== null) return defaultPrompt;
    try {
      const res = await fetch("/api/optimize-title/prompt");
      if (!res.ok) return "";
      const data = (await res.json()) as { prompt?: string };
      const content = data.prompt || "";
      setDefaultPrompt(content);
      return content;
    } catch {
      return "";
    }
  };

  const handleOptimize = async () => {
    if (!originalTitle.trim()) return;
    setOptimizing(true);
    try {
      const res = await fetch("/api/optimize-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: originalTitle,
          ...(promptTemplate.trim() ? { prompt: promptTemplate } : {}),
          ...(textModel ? { text_model: textModel } : {}),
        }),
      });
      const data = (await res.json()) as { optimized_title?: string; error?: string };
      if (!res.ok || data.error) throw new Error(data.error || "Title optimization failed");
      setOptimizedTitle(data.optimized_title || "");
    } catch (err) {
      addToast?.("error", (err as Error).message || "Title optimization failed");
    } finally {
      setOptimizing(false);
    }
  };

  const confirmTopLink = async (top: TextSearchResult) => {
    setMatchLabel("checking");
    setSiteImages([]);
    try {
      const res = await fetch("/api/scrape-site-images", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link: top.link }),
      });
      const data = (await res.json()) as { images?: string[]; error?: string };
      if (!res.ok || data.error) throw new Error(data.error || "Image scrape failed");
      setSiteImages(data.images || []);
      // pHash comparison against the eBay photos is ticket 07 — placeholder label for now
      setMatchLabel("unconfirmed");
    } catch (err) {
      setMatchLabel(null);
      addToast?.("error", (err as Error).message || "Failed to scrape site images");
    }
  };

  const handleSearch = async () => {
    const query = searchQuery();
    if (!query) {
      addToast?.("error", "Optimized title is empty — optimize or type a title first");
      return;
    }
    setSearching(true);
    setResults([]);
    setTopLink(null);
    setSiteImages([]);
    setMatchLabel(null);
    try {
      const res = await fetch("/api/serp-text-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          enabled_sites: enabledSites,
          site_priorities: sitePriority,
          max_results: maxResults,
        }),
      });
      const data = (await res.json()) as { results?: TextSearchResult[]; error?: string };
      if (!res.ok || data.error) throw new Error(data.error || "Search failed");
      // Whitelisted results only, already ordered by site priority by the backend
      const whitelisted = (data.results || []).filter((r) => r.site_type === "whitelisted");
      const skippedSites = new Set<string>();
      const filtered = whitelisted.filter((r) => {
        const key = threeDSiteKeyFromLink(r.link);
        if (key && siteStatus?.[key] && !siteStatus[key].ok) {
          skippedSites.add(key);
          return false;
        }
        return true;
      });
      setResults(filtered);
      if (skippedSites.size > 0) {
        addToast?.("info", `Skipped results from ${[...skippedSites].join(", ")} — site failed its operational test (see Settings > 3D File Sites)`);
      }
      if (filtered.length === 0) {
        if (skippedSites.size === 0) addToast?.("info", "No 3D file results found for this title");
        return;
      }
      const top = filtered[0];
      setTopLink(top);
      void confirmTopLink(top);
    } catch (err) {
      addToast?.("error", (err as Error).message || "Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleUseLink = () => {
    if (!topLink) return;
    onUseLink?.(topLink.link);
  };

  const togglePrompt = async () => {
    const next = !promptOpen;
    setPromptOpen(next);
    if (next && !promptTemplate) {
      const content = await loadDefaultPrompt();
      if (content) setPromptTemplate(content);
    }
  };

  return (
    <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-left"
      >
        <span className={`inline-block transition-transform ${open ? "rotate-90" : ""}`}>▸</span>
        <span className="text-lg font-semibold text-text-primary">Title Search</span>
      </button>
      {open && (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-text-muted">
            Search 3D file sites by listing title instead of reverse image search.
          </p>

          {/* Step 1 — Fetch eBay title + photos */}
          <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
            <p className="text-sm font-semibold text-text-primary">Step 1 — Fetch eBay Listing</p>
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
            {photos.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-xs text-text-muted">
                  {photos.length} photo{photos.length !== 1 ? "s" : ""} found
                </p>
                <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8">
                  {photos.map((url, i) => (
                    <div
                      key={`${i}-${url}`}
                      className="aspect-square overflow-hidden rounded-lg border-2 border-border-default"
                    >
                      <img src={url} alt={`Photo ${i + 1}`} className="h-full w-full object-cover" />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Step 2 — Optimize title + search */}
          {originalTitle && (
            <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
              <p className="text-sm font-semibold text-text-primary">Step 2 — Optimize Title &amp; Search</p>
              <div className="flex flex-col gap-1">
                <p className="text-xs font-semibold text-text-muted">Original title</p>
                <p className="text-sm text-text-primary">{originalTitle}</p>
              </div>
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  aria-expanded={promptOpen}
                  onClick={togglePrompt}
                  className="flex w-fit items-center gap-2 text-left text-xs font-semibold text-text-muted"
                >
                  <span className={`inline-block transition-transform ${promptOpen ? "rotate-90" : ""}`}>▸</span>
                  Haiku prompt (editable)
                </button>
                {promptOpen && (
                  <textarea
                    aria-label="Haiku prompt"
                    className="min-h-40 rounded-lg border-2 border-border-default bg-surface-panel px-3 py-2 font-mono text-xs text-text-primary transition-colors focus:border-primary focus:outline-none"
                    value={promptTemplate}
                    onChange={(e) => setPromptTemplate(e.target.value)}
                    placeholder="Loading default prompt..."
                  />
                )}
              </div>
              <div className="flex items-end gap-3">
                <div className="flex flex-1 flex-col gap-1">
                  <label htmlFor="title-search-optimized" className="text-xs font-semibold text-text-muted">
                    Optimized title (editable) — " 3d file" is appended on search
                  </label>
                  <input
                    id="title-search-optimized"
                    type="text"
                    className="rounded-lg border-2 border-border-default bg-surface-panel px-4 py-2 text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover"
                    value={optimizedTitle}
                    onChange={(e) => setOptimizedTitle(e.target.value)}
                    placeholder="Optimize the title or type a search title..."
                    disabled={optimizing}
                  />
                </div>
                <button
                  type="button"
                  className={btnPillSm}
                  onClick={handleOptimize}
                  disabled={optimizing || !originalTitle.trim()}
                >
                  {optimizing ? "Optimizing..." : "Optimize"}
                </button>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex flex-col gap-1">
                  <label htmlFor="title-search-max-results" className="text-xs font-semibold text-text-muted">
                    Max results
                  </label>
                  <input
                    id="title-search-max-results"
                    type="number"
                    min={1}
                    className="w-24 rounded-lg border-2 border-border-default bg-surface-panel px-3 py-2 text-text-primary transition-colors focus:border-primary focus:outline-none"
                    value={maxResults}
                    onChange={(e) => setMaxResults(Math.max(1, parseInt(e.target.value, 10) || DEFAULT_MAX_RESULTS))}
                  />
                </div>
                <button
                  type="button"
                  className={btnPill}
                  onClick={handleSearch}
                  disabled={searching || !optimizedTitle.trim()}
                >
                  {searching ? "Searching..." : "Search"}
                </button>
              </div>
              {results.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-xs text-text-muted">
                    Whitelisted results ({results.length}), ordered by site priority
                  </p>
                  <ol className="flex flex-col gap-2">
                    {results.map((r, i) => {
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
                            <p className="truncate text-xs text-text-muted">{hostname}</p>
                          </div>
                        </li>
                      );
                    })}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* Step 3 — Image confirmation (top-priority link) */}
          {topLink && (
            <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
              <p className="text-sm font-semibold text-text-primary">Step 3 — Confirm Match</p>
              <div className="flex items-center gap-2">
                <a
                  href={topLink.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="truncate text-sm font-medium text-primary hover:underline"
                >
                  {topLink.title || topLink.link}
                </a>
                {matchLabel === "checking" && (
                  <span className="shrink-0 rounded-full bg-surface-hover px-2 py-0.5 text-xs font-medium text-text-muted">
                    Checking...
                  </span>
                )}
                {matchLabel === "confirmed" && (
                  <span className="shrink-0 rounded-full bg-green-500/15 px-2 py-0.5 text-xs font-medium text-green-400">
                    Confirmed image match
                  </span>
                )}
                {matchLabel === "unconfirmed" && (
                  <span className="shrink-0 rounded-full bg-yellow-500/15 px-2 py-0.5 text-xs font-medium text-yellow-400">
                    Unconfirmed title match
                  </span>
                )}
              </div>
              {siteImages.length > 0 && (
                <div className="grid grid-cols-4 gap-2 sm:grid-cols-6 md:grid-cols-8">
                  {siteImages.map((url, i) => (
                    <div
                      key={`${i}-${url}`}
                      className="aspect-square overflow-hidden rounded-lg border-2 border-border-default"
                    >
                      <img src={url} alt={`Site image ${i + 1}`} className="h-full w-full object-cover" />
                    </div>
                  ))}
                </div>
              )}

              {/* Step 4 — Forward to download step */}
              <div className="flex justify-end">
                <button type="button" className={btnPillSm} onClick={handleUseLink}>
                  Use this link →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default TitleSearchPipeline;
