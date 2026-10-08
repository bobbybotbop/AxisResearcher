import { useState } from "react";
import MessageBarInput from "./MessageBarInput";
import { btnPill, btnPillSm } from "../styles/buttonPill";

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
  const [step3Loading, setStep3Loading] = useState(false);
  const [step3Result, setStep3Result] = useState<{ filename: string; bytes: number } | null>(null);
  const [step3Error, setStep3Error] = useState<string | null>(null);

  // True when a result link can be forwarded to Step 3
  const canForwardToStep3 = (link: string) =>
    /thingiverse\.com\/thing[:/]\d+/.test(link) ||
    /printables\.com\/model\/\d+/.test(link);

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
        body: JSON.stringify({ image_url: url }),
      });
      const data = await res.json() as { error?: string; results?: SearchResult[] };
      if (!res.ok || data.error) throw new Error(data.error || "Search failed");
      const filtered = (data.results || []).filter(r => r.site_type === "whitelisted");
      setStep2Results(filtered);
      if (filtered.length === 0) addToast?.("info", "No 3D file results found for this image");
    } catch (err) {
      addToast?.("error", (err as Error).message || "Search failed");
    } finally {
      setStep2Loading(false);
    }
  };

  const handleStep3Download = async () => {
    const link = step3Url.trim();
    if (!link || !step3Supported) return;
    setStep3Loading(true);
    setStep3Result(null);
    setStep3Error(null);
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
      setStep3Loading(false);
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
                  key={url}
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
                  onClick={() => setStep2ImageUrl(step1Selected!)}
                >
                  Use photo in Step 2 →
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      {/* steps 2 and 3 go here — added in tasks 3–4 */}
    </div>
  );
}

export default ThreeDFileFinder;
