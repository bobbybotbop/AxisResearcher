# 3D File Finder Independent Step Panels — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure `ThreeDFileFinder.tsx` into three always-visible, independently operable step panels so each step of the 3D file download workflow can be tested in isolation.

**Architecture:** Single component rewrite — all changes live in `ThreeDFileFinder.tsx`. State is split into three namespaced groups (`step1*`, `step2*`, `step3*`). Forward affordances ("Use photo in Step 2 →" and "Use →") are plain `setState` calls that pre-fill the next panel's input without triggering that step automatically.

**Tech Stack:** React 18 + TypeScript, Tailwind v4, existing `MessageBarInput` and `btnPill`/`btnPillSm` style utilities.

---

## Files

- Modify: `frontend/src/components/ThreeDFileFinder.tsx` (full rewrite)

No other files change.

---

## Task 1: Replace state, imports, and handlers

This task rewrites all the internal logic of the component — state declarations, the three async handlers, and two pure helpers. The JSX `return` will be replaced in the next task.

**Files:**
- Modify: `frontend/src/components/ThreeDFileFinder.tsx`

- [ ] **Step 1: Open the file and verify what currently exists**

Read `frontend/src/components/ThreeDFileFinder.tsx`. Confirm it has these five state variables at the top: `linkValue`, `photos`, `listingTitle`, `fetchingPhotos`, `selectedPhoto`, `searchResults`, `searching`, `downloadingLink`. These will all be replaced.

- [ ] **Step 2: Replace the entire file with the new state, imports, and handlers**

Write the following to `frontend/src/components/ThreeDFileFinder.tsx`. This is the complete new file — handlers are implemented but the `return` renders a placeholder so the component compiles while tasks 2–4 fill in the panels:

```tsx
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

  // True when step3Url is a supported downloadable pattern
  const step3Supported =
    /thingiverse\.com\/thing[:/]\d+/.test(step3Url.trim()) ||
    /printables\.com\/model\/\d+/.test(step3Url.trim());

  // True when a result link can be forwarded to Step 3
  const canForwardToStep3 = (link: string) =>
    /thingiverse\.com\/thing[:/]\d+/.test(link) ||
    /printables\.com\/model\/\d+/.test(link);

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
      {/* panels go here — added in tasks 2–4 */}
    </div>
  );
}

export default ThreeDFileFinder;
```

- [ ] **Step 3: Verify TypeScript compiles with no errors**

Check the VS Code Problems panel (or run `cd frontend && npx tsc --noEmit`) and confirm zero errors in `ThreeDFileFinder.tsx`. The component renders an empty shell — that's expected at this point.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ThreeDFileFinder.tsx
git commit -m "refactor: rewrite ThreeDFileFinder state and handlers for independent step panels"
```

---

## Task 2: Add Step 1 panel

Replace the `{/* panels go here */}` comment with the Step 1 card.

**Files:**
- Modify: `frontend/src/components/ThreeDFileFinder.tsx`

- [ ] **Step 1: Replace the placeholder comment with the Step 1 panel**

In the `return`, replace:
```tsx
      {/* panels go here — added in tasks 2–4 */}
```

with:
```tsx
      {/* Step 1 — Fetch eBay Photos */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 1 — Fetch eBay Photos</p>
        <form onSubmit={handleStep1Submit} className="flex items-end gap-3">
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
                  onClick={() => setStep1Selected(url)}
                  className={`aspect-square overflow-hidden rounded-lg border-2 transition-all ${
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
```

- [ ] **Step 2: Run the dev server and verify Step 1 panel visually**

```bash
npm run dev
```

Open `http://localhost:4000` in a browser, navigate to the Testing tab. Verify:
- Step 1 card is visible with "Step 1 — Fetch eBay Photos" header
- Text input and a submit button render
- Paste a real eBay item ID and press Enter — photo grid appears, first photo is ring-highlighted
- Clicking a different photo moves the ring highlight
- "Use photo in Step 2 →" button appears below the grid once a photo is selected; it is absent before photos load

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ThreeDFileFinder.tsx
git commit -m "feat: add Step 1 panel to ThreeDFileFinder (fetch eBay photos)"
```

---

## Task 3: Add Step 2 panel

Replace the steps 2/3 placeholder comment with the Step 2 card.

**Files:**
- Modify: `frontend/src/components/ThreeDFileFinder.tsx`

- [ ] **Step 1: Replace the placeholder comment with the Step 2 panel**

Replace:
```tsx
      {/* steps 2 and 3 go here — added in tasks 3–4 */}
```

with:
```tsx
      {/* Step 2 — Reverse Image Search */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 2 — Reverse Image Search</p>
        <div className="flex items-center gap-3">
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
              className="h-8 w-8 shrink-0 rounded object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              onLoad={(e) => { (e.target as HTMLImageElement).style.display = ""; }}
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
        </div>
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
                        className={btnPillSm}
                        onClick={() => setStep3Url(r.link)}
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
      {/* step 3 goes here — added in task 4 */}
```

- [ ] **Step 2: Verify Step 2 panel visually**

With the dev server running, check the Testing tab. Verify:
- Step 2 card renders below Step 1 with "Step 2 — Reverse Image Search" header
- Pasting an image URL into the input shows a small thumbnail preview next to the field
- Pasting a non-image URL hides the thumbnail (onError fires)
- Search button is disabled when the input is empty
- After a successful search (real SERP API key required), results list appears with green "3D site" badges
- Printables/Thingiverse results show a "Use →" button; makerworld/yeggi/others do not
- Clicking "Use →" fills the Step 3 URL input (Step 3 panel not yet rendered, but verify `step3Url` state updates by clicking "Use photo in Step 2 →" from Step 1 and confirming Step 2's input pre-fills)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ThreeDFileFinder.tsx
git commit -m "feat: add Step 2 panel to ThreeDFileFinder (reverse image search)"
```

---

## Task 4: Add Step 3 panel and wire forward affordances end to end

Replace the final placeholder comment with the Step 3 card. After this task the full pipeline is live.

**Files:**
- Modify: `frontend/src/components/ThreeDFileFinder.tsx`

- [ ] **Step 1: Replace the placeholder comment with the Step 3 panel**

Replace:
```tsx
      {/* step 3 goes here — added in task 4 */}
```

with:
```tsx
      {/* Step 3 — Download 3D File */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 3 — Download 3D File</p>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <MessageBarInput
              value={step3Url}
              onChange={(val) => {
                setStep3Url(val);
                setStep3Result(null);
                setStep3Error(null);
              }}
              placeholder="Paste printables.com or thingiverse.com URL..."
              disabled={step3Loading}
              loading={step3Loading}
              aria-label="3D site URL"
              fullWidth
            />
          </div>
          <button
            type="button"
            className={btnPill}
            onClick={handleStep3Download}
            disabled={!step3Supported || step3Loading}
          >
            {step3Loading ? "Downloading..." : "Download"}
          </button>
        </div>
        <p className="text-xs">
          {step3Url.trim() && !step3Supported ? (
            <span className="text-amber-400">Unsupported site</span>
          ) : (
            <span className="text-text-muted">Supported: printables.com, thingiverse.com</span>
          )}
        </p>
        {step3Result && (
          <p className="text-sm text-green-400">
            Downloaded: {step3Result.filename} ({formatBytes(step3Result.bytes)})
          </p>
        )}
        {step3Error && (
          <p className="text-sm text-red-400">{step3Error}</p>
        )}
      </div>
```

- [ ] **Step 2: Verify Step 3 panel visually — standalone download**

With the dev server running, navigate to the Testing tab. Verify Step 3 in isolation:
- Card renders with "Step 3 — Download 3D File" header
- Helper text reads "Supported: printables.com, thingiverse.com" when input is empty
- Paste a random URL (e.g. `https://makerworld.com/en/models/123`) — "Unsupported site" warning appears in amber and Download button stays disabled
- Paste `https://www.printables.com/model/123456` — warning disappears, Download button becomes active
- Click Download — "Downloading..." appears, then either a zip file downloads and "Downloaded: filename.zip (X MB)" appears inline, or an inline red error message appears (no toast)
- Editing the URL after a successful download clears the success/error line

- [ ] **Step 3: Verify the full pipeline end to end**

Run the complete flow:
1. Step 1: paste an eBay listing URL, fetch photos, select one, click "Use photo in Step 2 →" — Step 2 input pre-fills
2. Step 2: click Search — results appear, click "Use →" on a printables/thingiverse result — Step 3 input pre-fills
3. Step 3: click Download — file downloads, success message appears inline

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ThreeDFileFinder.tsx
git commit -m "feat: add Step 3 panel to ThreeDFileFinder (download 3D file)"
```

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Task |
|---|---|
| Three always-visible stacked panels | Tasks 2–4 |
| Step 1: eBay URL input + photo grid + selection | Task 2 |
| Step 1: "Use photo in Step 2 →" button (absent when no selection) | Task 2 |
| Step 2: image URL input + thumbnail preview with onError hide | Task 3 |
| Step 2: search results filtered to whitelisted sites only | Task 1 (handler) |
| Step 2: "Use →" only on printables/thingiverse results | Task 3 |
| Step 3: URL input + inline validation note | Task 4 |
| Step 3: Download button disabled when unsupported or empty | Task 4 |
| Step 3: inline success line with filename + size | Task 4 |
| Step 3: inline error (no toast) | Task 4 |
| Editing Step 3 URL clears previous result/error | Task 4 |
| `fetchWithProgress` import removed | Task 1 |
| No backend changes | N/A |
| No App.tsx changes | N/A |

All requirements covered.

### Placeholder scan

No TBDs, no "implement later", no vague steps. Every code block is complete.

### Type consistency

- `canForwardToStep3` is defined in Task 1 and used in Task 3 — matches.
- `formatBytes` defined in Task 1, used in Task 4 — matches.
- `step3Supported` derived value defined in Task 1, used in Task 4 — matches.
- `SearchResult` interface defined in Task 1, used as `SearchResult[]` in Task 1 and rendered in Task 3 — matches.
- `step1Selected` is `string | null`, forwarded via `setStep2ImageUrl(step1Selected!)` — the non-null assertion is safe because the button is only rendered when `step1Selected` is truthy.
