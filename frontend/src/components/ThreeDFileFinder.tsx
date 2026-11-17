import { useEffect, useRef, useState } from "react";
import JSZip from "jszip";
import MessageBarInput from "./MessageBarInput";
import RenderProfileDropdown from "./RenderProfileDropdown";
import StudioRenderPreview, { type StudioRenderPreviewHandle } from "./StudioRenderPreview";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import { DOWNLOAD_MODE_FILES, DOWNLOAD_MODE_FULL_ZIP, DOWNLOAD_MODE_SINGLE_FILE, threeDSiteKeyFromLink, type DownloadMode, type ThreeDSiteStatus } from "../constants/files3d";
import {
  modelExtensionOf,
  NATIVE_RENDER_EXTENSIONS,
  RENDER_AMBIENT_MAX,
  RENDER_CANDIDATE_EXTENSIONS,
  RENDER_ENERGY_MAX,
  RENDER_EXPOSURE_MAX,
  RENDER_EXPOSURE_MIN,
  RENDER_FINISH_OPTIONS,
  RENDER_FOV_MAX,
  RENDER_FOV_MIN,
<<<<<<< HEAD
  RENDER_LAYER_HEIGHT_MM_MAX,
  RENDER_LAYER_HEIGHT_MM_MIN,
  RENDER_RESOLUTION_OPTIONS,
=======
>>>>>>> integration/render-profiles
  RENDER_SETTINGS_DEFAULTS,
  RENDER_SETTINGS_SAVE_DEBOUNCE_MS,
  RENDER_SHADOW_SOFTNESS_MAX,
  RENDER_SHADOW_SOFTNESS_MIN,
  RENDER_STATUS_POLL_DEADLINE_MS,
  RENDER_STATUS_POLL_INTERVAL_MS,
  RENDERABLE_FORMATS_HINT,
<<<<<<< HEAD
  type RenderFinish,
=======
  type RenderProfileSettings,
>>>>>>> integration/render-profiles
} from "../constants/render";

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

// All renderable entries (zip contents or a single file), best-ranked first.
// Empty when nothing renderable is inside.
const pickRenderCandidates = (entries: UnzippedEntry[]): File[] =>
  entries
    .filter((e) => RENDER_CANDIDATE_EXTENSIONS.includes(modelExtensionOf(e.path[e.path.length - 1])))
    .sort(
      (a, b) =>
        RENDER_CANDIDATE_EXTENSIONS.indexOf(modelExtensionOf(a.path[a.path.length - 1])) -
        RENDER_CANDIDATE_EXTENSIONS.indexOf(modelExtensionOf(b.path[b.path.length - 1])),
    )
    .map((e) => new File([e.data], e.path[e.path.length - 1]));

interface RenderSettingsPatch {
  color?: string;
  roughness?: number;
  resolution?: number;
  fov?: number;
  finish?: RenderFinish;
  layer_height_mm?: number;
  layer_depth?: number;
  key_energy?: number;
  fill_energy?: number;
  rim_energy?: number;
  ambient?: number;
  shadow?: boolean;
  shadow_softness?: number;
  exposure?: number;
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

  // Step 4 — Studio Render (renderFile = best renderable file from the Step 3 download;
  // previewFile = the Render Mesh the preview shows — the upload itself for native
  // formats, otherwise the STL the backend normalized it to)
  const [renderFile, setRenderFile] = useState<File | null>(null);
  const [renderCandidates, setRenderCandidates] = useState<File[]>([]);
  const [renderFileChecked, setRenderFileChecked] = useState(false);
  // True when the Step 3 download contained .amf files (unsupported, but worth
  // calling out explicitly in the Step 4 empty state)
  const [downloadHasAmf, setDownloadHasAmf] = useState(false);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [previewConverting, setPreviewConverting] = useState(false);
  const [renderFov, setRenderFov] = useState(RENDER_SETTINGS_DEFAULTS.fov);
  const [previewReady, setPreviewReady] = useState(false);
  const previewRef = useRef<StudioRenderPreviewHandle>(null);
  const [step4Loading, setStep4Loading] = useState(false);
  const [step4Image, setStep4Image] = useState<{ url: string; filename: string } | null>(null);
  const [step4Error, setStep4Error] = useState<string | null>(null);

  // Step 4 — Render Settings (persisted in listingPreferences.json via /api/render-settings)
  const [renderColor, setRenderColor] = useState(RENDER_SETTINGS_DEFAULTS.color);
  const [renderRoughness, setRenderRoughness] = useState(RENDER_SETTINGS_DEFAULTS.roughness);
  const [renderResolution, setRenderResolution] = useState(RENDER_SETTINGS_DEFAULTS.resolution);
  const [renderFinish, setRenderFinish] = useState<RenderFinish>(RENDER_SETTINGS_DEFAULTS.finish);
  const [renderLayerHeightMm, setRenderLayerHeightMm] = useState(RENDER_SETTINGS_DEFAULTS.layerHeightMm);
  const [renderLayerDepth, setRenderLayerDepth] = useState(RENDER_SETTINGS_DEFAULTS.layerDepth);
  const [renderKeyEnergy, setRenderKeyEnergy] = useState(RENDER_SETTINGS_DEFAULTS.keyEnergy);
  const [renderFillEnergy, setRenderFillEnergy] = useState(RENDER_SETTINGS_DEFAULTS.fillEnergy);
  const [renderRimEnergy, setRenderRimEnergy] = useState(RENDER_SETTINGS_DEFAULTS.rimEnergy);
  const [renderAmbient, setRenderAmbient] = useState(RENDER_SETTINGS_DEFAULTS.ambient);
  const [renderShadow, setRenderShadow] = useState(RENDER_SETTINGS_DEFAULTS.shadow);
  const [renderShadowSoftness, setRenderShadowSoftness] = useState(RENDER_SETTINGS_DEFAULTS.shadowSoftness);
  const [renderExposure, setRenderExposure] = useState(RENDER_SETTINGS_DEFAULTS.exposure);
  const renderSettingsSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Step 4 — view switching: the profile dropdown or the Profile Editor
  // (placeholder until ticket 05). editingProfile carries which profile the
  // editor opened for: a name, null for "Current Settings", or "create".
  const [step4View, setStep4View] = useState<"dropdown" | "editor">("dropdown");
  const [editingProfile, setEditingProfile] = useState<string | null | "create">(null);

  // Load persisted Render Settings once on mount; fall back to spec defaults on failure
  useEffect(() => {
    let cancelled = false;
    fetch("/api/render-settings")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        if (typeof data.color === "string") setRenderColor(data.color);
        if (typeof data.roughness === "number") setRenderRoughness(data.roughness);
        if (typeof data.resolution === "number") setRenderResolution(data.resolution);
        if (typeof data.fov === "number") setRenderFov(data.fov);
        if (data.finish === "smooth" || data.finish === "layer-lines") setRenderFinish(data.finish);
        if (typeof data.layer_height_mm === "number") setRenderLayerHeightMm(data.layer_height_mm);
        if (typeof data.layer_depth === "number") setRenderLayerDepth(data.layer_depth);
        if (typeof data.key_energy === "number") setRenderKeyEnergy(data.key_energy);
        if (typeof data.fill_energy === "number") setRenderFillEnergy(data.fill_energy);
        if (typeof data.rim_energy === "number") setRenderRimEnergy(data.rim_energy);
        if (typeof data.ambient === "number") setRenderAmbient(data.ambient);
        if (typeof data.shadow === "boolean") setRenderShadow(data.shadow);
        if (typeof data.shadow_softness === "number") setRenderShadowSoftness(data.shadow_softness);
        if (typeof data.exposure === "number") setRenderExposure(data.exposure);
      })
      .catch(() => { /* keep spec defaults */ });
    return () => { cancelled = true; };
  }, []);

  // Persist changes debounced (slider/color input fire many events while dragging)
  const persistRenderSettings = (patch: RenderSettingsPatch) => {
    if (renderSettingsSaveTimer.current) clearTimeout(renderSettingsSaveTimer.current);
    renderSettingsSaveTimer.current = setTimeout(() => {
      fetch("/api/render-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      }).catch(() => { /* persistence is best-effort; the control still applies to renders */ });
    }, RENDER_SETTINGS_SAVE_DEBOUNCE_MS);
  };

  // Selecting a Render Profile copies its values into Current Settings: the
  // whole settings object is POSTed verbatim to the flat settings (so fields
  // added later need no UI changes), and known fields update local state so
  // the preview/Render button reflect the selection immediately.
  const handleProfileSelect = (name: string | null, settings: RenderProfileSettings | null) => {
    if (name === null || !settings) return; // "Current Settings": flat settings are already the source of truth
    if (renderSettingsSaveTimer.current) clearTimeout(renderSettingsSaveTimer.current);
    fetch("/api/render-settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    }).catch(() => { /* the selection still applies locally for this session */ });
    if (typeof settings.color === "string") setRenderColor(settings.color);
    if (typeof settings.roughness === "number") setRenderRoughness(settings.roughness);
    if (typeof settings.resolution === "number") setRenderResolution(settings.resolution);
    if (typeof settings.fov === "number") setRenderFov(settings.fov);
  };

  const resetStep4 = () => {
    setRenderFile(null);
    setRenderCandidates([]);
    setRenderFileChecked(false);
    setDownloadHasAmf(false);
    setPreviewFile(null);
    setPreviewConverting(false);
    setPreviewReady(false);
    setStep4Loading(false);
    setStep4Image(null);
    setStep4Error(null);
  };

  // Normalize non-native formats server-side so the preview shows the same
  // converted Render Mesh that Blender renders (the backend caches it, so the
  // Render request below doesn't convert twice)
  useEffect(() => {
    if (!renderFile || NATIVE_RENDER_EXTENSIONS.includes(modelExtensionOf(renderFile.name))) {
      setPreviewFile(renderFile);
      setPreviewConverting(false);
      return;
    }
    let cancelled = false;
    setPreviewFile(null);
    setPreviewConverting(true);
    setStep4Error(null);
    const form = new FormData();
    form.append("file", renderFile);
    fetch("/api/render-preview", { method: "POST", body: form })
      .then(async (res) => {
        if (!res.ok) {
          const data = (await res.json().catch(() => null)) as { error?: string } | null;
          throw new Error(data?.error || "Could not convert the model for preview");
        }
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const stlName = renderFile.name.replace(/\.[^.]+$/, "") + ".stl";
        setPreviewFile(new File([blob], stlName));
        setPreviewConverting(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setPreviewConverting(false);
        setStep4Error((err as Error).message || "Could not convert the model for preview");
      });
    return () => { cancelled = true; };
  }, [renderFile]);

  // Auto-pick the best-ranked model; the dropdown lets the user switch when
  // a download contains several renderable candidates
  const applyRenderCandidates = (candidates: File[]) => {
    setRenderCandidates(candidates);
    setRenderFile(candidates[0] ?? null);
    setRenderFileChecked(true);
    setPreviewReady(false);
  };

  // Load a user-chosen local file (single model or zip) into Step 4 through
  // the same pipeline as a Step 3 download
  const handleCustomRenderFile = async (file: File) => {
    setStep4Error(null);
    try {
      const entries = await unzipBlob(file, file.name);
      setDownloadHasAmf(entries.some((e) => modelExtensionOf(e.path[e.path.length - 1]) === ".amf"));
      applyRenderCandidates(pickRenderCandidates(entries));
    } catch (err) {
      setStep4Error((err as Error).message || "Could not read that file");
    }
  };

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
    resetStep4();
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
        setDownloadHasAmf(entries.some((e) => modelExtensionOf(e.path[e.path.length - 1]) === ".amf"));
        applyRenderCandidates(pickRenderCandidates(entries));
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
      const entries = await unzipBlob(blob, filename);
      setDownloadHasAmf(entries.some((e) => modelExtensionOf(e.path[e.path.length - 1]) === ".amf"));
      applyRenderCandidates(pickRenderCandidates(entries));
      setStep3Result({ filename, bytes: blob.size });
    } catch (err) {
      setStep3Error((err as Error).message || "Download failed");
    } finally {
      setStep3LoadingMode(null);
    }
  };

  const handleStep4Render = async () => {
    if (!renderFile || step4Loading) return;
    setStep4Loading(true);
    setStep4Error(null);
    setStep4Image(null);
    try {
      const form = new FormData();
      form.append("file", renderFile);
      form.append("color", renderColor);
      form.append("roughness", String(renderRoughness));
      form.append("resolution", String(renderResolution));
      // Camera Intent: the angle the user framed in the preview
      const intent = previewRef.current?.getCameraIntent();
      if (intent) {
        form.append("camera_position", intent.position.join(","));
        form.append("camera_target", intent.target.join(","));
      }
      form.append("fov", String(renderFov));
      form.append("finish", renderFinish);
      form.append("layer_height_mm", String(renderLayerHeightMm));
      form.append("layer_depth", String(renderLayerDepth));
      form.append("key_energy", String(renderKeyEnergy));
      form.append("fill_energy", String(renderFillEnergy));
      form.append("rim_energy", String(renderRimEnergy));
      form.append("ambient", String(renderAmbient));
      form.append("shadow", String(renderShadow));
      form.append("shadow_softness", String(renderShadowSoftness));
      form.append("exposure", String(renderExposure));
      const res = await fetch("/api/render", { method: "POST", body: form });
      const data = await res.json() as { task_id?: string; error?: string };
      if (!res.ok || data.error || !data.task_id) throw new Error(data.error || "Failed to start the render");

      const deadline = Date.now() + RENDER_STATUS_POLL_DEADLINE_MS;
      for (;;) {
        await new Promise((r) => setTimeout(r, RENDER_STATUS_POLL_INTERVAL_MS));
        const statusRes = await fetch(`/api/render-status/${data.task_id}`);
        const status = await statusRes.json() as { status?: string; image?: string; filename?: string; error?: string };
        if (!statusRes.ok) throw new Error(status.error || "Lost track of the render job");
        if (status.status === "completed" && status.image && status.filename) {
          setStep4Image({ url: status.image, filename: status.filename });
          break;
        }
        if (status.status === "failed") throw new Error(status.error || "Render failed");
        if (Date.now() > deadline) throw new Error("Render is taking too long — check that Blender is installed and the backend is running");
      }
    } catch (err) {
      setStep4Error((err as Error).message || "Render failed");
    } finally {
      setStep4Loading(false);
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
                          resetStep4();
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
                resetStep4();
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
      {/* Step 4 — Studio Render */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 4 — Studio Render</p>
        {step4View === "editor" ? (
          // Profile Editor placeholder — ticket 05 replaces this block with the
          // real editor (3DBenchy viewer + settings panel + Save buttons)
          <div className="flex flex-col gap-3 rounded-lg border border-border-default p-3">
            <p className="text-sm text-text-primary">
              {editingProfile === "create"
                ? "Create new profile"
                : editingProfile === null
                  ? "Edit Current Settings"
                  : `Edit profile: ${editingProfile}`}
            </p>
            <p className="text-xs text-text-muted">The Profile Editor arrives in the next ticket.</p>
            <div>
              <button type="button" className={btnPillSm} onClick={() => setStep4View("dropdown")}>
                ← Back to profiles
              </button>
            </div>
          </div>
        ) : (
          /* Render Profile — selecting one copies its values into Current
             Settings (the flat settings); camera angle is captured from the preview below */
          <div className="flex items-center gap-3 rounded-lg border border-border-default p-3">
            <RenderProfileDropdown
              onSelect={handleProfileSelect}
              onEdit={(mode, name) => {
                setEditingProfile(mode === "create" ? "create" : name);
                setStep4View("editor");
              }}
              addToast={addToast}
            />
<<<<<<< HEAD
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Glossiness ({(1 - renderRoughness).toFixed(2)})</span>
            {/* Slider shows glossiness; the persisted/wire value is Principled
                roughness (glossiness = 1 − roughness), so dragging up = glossier */}
            <input
              type="range"
              aria-label="Glossiness"
              min={0}
              max={1}
              step={0.05}
              value={1 - renderRoughness}
              onChange={(e) => {
                const roughness = 1 - Number(e.target.value);
                setRenderRoughness(roughness);
                persistRenderSettings({ roughness });
              }}
              className="w-40 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Resolution</span>
            <select
              aria-label="Resolution"
              value={renderResolution}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderResolution(value);
                persistRenderSettings({ resolution: value });
              }}
              className="rounded border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary"
            >
              {RENDER_RESOLUTION_OPTIONS.map((size) => (
                <option key={size} value={size}>{size} × {size}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Finish</span>
            <select
              aria-label="Surface finish"
              value={renderFinish}
              onChange={(e) => {
                const value = e.target.value as RenderFinish;
                setRenderFinish(value);
                persistRenderSettings({ finish: value });
              }}
              className="rounded border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary"
            >
              {RENDER_FINISH_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          {renderFinish === "layer-lines" && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-text-muted">Layer height ({renderLayerHeightMm.toFixed(2)}mm)</span>
                <input
                  type="range"
                  aria-label="Layer height"
                  min={RENDER_LAYER_HEIGHT_MM_MIN}
                  max={RENDER_LAYER_HEIGHT_MM_MAX}
                  step={0.01}
                  value={renderLayerHeightMm}
                  onChange={(e) => {
                    const value = Number(e.target.value);
                    setRenderLayerHeightMm(value);
                    persistRenderSettings({ layer_height_mm: value });
                  }}
                  className="w-32 accent-primary"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-text-muted">Line depth ({renderLayerDepth.toFixed(2)})</span>
                <input
                  type="range"
                  aria-label="Line depth"
                  min={0}
                  max={1}
                  step={0.05}
                  value={renderLayerDepth}
                  onChange={(e) => {
                    const value = Number(e.target.value);
                    setRenderLayerDepth(value);
                    persistRenderSettings({ layer_depth: value });
                  }}
                  className="w-32 accent-primary"
                />
              </label>
            </>
          )}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Key light ({renderKeyEnergy})</span>
            <input
              type="range"
              aria-label="Key light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={renderKeyEnergy}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderKeyEnergy(value);
                persistRenderSettings({ key_energy: value });
              }}
              className="w-32 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Fill light ({renderFillEnergy})</span>
            <input
              type="range"
              aria-label="Fill light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={renderFillEnergy}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderFillEnergy(value);
                persistRenderSettings({ fill_energy: value });
              }}
              className="w-32 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Rim light ({renderRimEnergy})</span>
            <input
              type="range"
              aria-label="Rim light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={renderRimEnergy}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderRimEnergy(value);
                persistRenderSettings({ rim_energy: value });
              }}
              className="w-32 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Ambient ({renderAmbient.toFixed(2)})</span>
            <input
              type="range"
              aria-label="Ambient strength"
              min={0}
              max={RENDER_AMBIENT_MAX}
              step={0.05}
              value={renderAmbient}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderAmbient(value);
                persistRenderSettings({ ambient: value });
              }}
              className="w-32 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Exposure ({renderExposure.toFixed(2)})</span>
            <input
              type="range"
              aria-label="Exposure"
              min={RENDER_EXPOSURE_MIN}
              max={RENDER_EXPOSURE_MAX}
              step={0.05}
              value={renderExposure}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRenderExposure(value);
                persistRenderSettings({ exposure: value });
              }}
              className="w-32 accent-primary"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Shadow</span>
            <input
              type="checkbox"
              aria-label="Shadow"
              checked={renderShadow}
              onChange={(e) => {
                setRenderShadow(e.target.checked);
                persistRenderSettings({ shadow: e.target.checked });
              }}
              className="h-5 w-5 accent-primary"
            />
          </label>
          {renderShadow && (
            <label className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Shadow softness ({renderShadowSoftness.toFixed(1)})</span>
              <input
                type="range"
                aria-label="Shadow softness"
                min={RENDER_SHADOW_SOFTNESS_MIN}
                max={RENDER_SHADOW_SOFTNESS_MAX}
                step={0.1}
                value={renderShadowSoftness}
                onChange={(e) => {
                  const value = Number(e.target.value);
                  setRenderShadowSoftness(value);
                  persistRenderSettings({ shadow_softness: value });
                }}
                className="w-32 accent-primary"
              />
            </label>
          )}
        </div>
=======
          </div>
        )}
>>>>>>> integration/render-profiles
        <div className="flex items-center gap-3">
          <button
            type="button"
            className={btnPill}
            onClick={handleStep4Render}
            disabled={!renderFile || !previewFile || !previewReady || step4Loading}
          >
            {step4Loading ? "Rendering..." : "Render"}
          </button>
          <p className="text-xs text-text-muted">
            {renderFile
              ? previewConverting
                ? `Converting ${renderFile.name} for preview...`
                : previewReady
                  ? `Ready to render: ${renderFile.name} (${formatBytes(renderFile.size)})`
                  : "Loading preview..."
              : renderFileChecked
                ? downloadHasAmf
                  ? `.amf is not supported — this download contains .amf 3D files but no supported model (supported: ${RENDERABLE_FORMATS_HINT})`
                  : `No renderable file (${RENDERABLE_FORMATS_HINT}) in this download`
                : "Download a model in Step 3, or test with your own file"}
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-text-muted">
          Test your own file:
          <input
            type="file"
            accept=".stl,.obj,.ply,.step,.stp,.3mf,.zip"
            aria-label="Test with your own 3D file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleCustomRenderFile(file);
              e.target.value = ""; // allow re-picking the same file
            }}
            className="text-xs text-text-muted file:mr-2 file:rounded-full file:border file:border-border-default file:bg-surface-panel file:px-3 file:py-1 file:text-xs file:text-text-primary"
          />
        </label>
        {renderCandidates.length > 1 && renderFile && (
          <label className="flex items-center gap-2 text-xs text-text-muted">
            Model to render:
            <select
              className="rounded border border-border-default bg-surface-panel px-2 py-1 text-xs text-text-primary"
              value={renderCandidates.indexOf(renderFile)}
              onChange={(e) => {
                setRenderFile(renderCandidates[Number(e.target.value)]);
                setPreviewReady(false);
              }}
              aria-label="Model to render"
            >
              {renderCandidates.map((candidate, i) => (
                <option key={`${i}-${candidate.name}`} value={i}>
                  {candidate.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {renderFile && previewFile && (
          <>
            <StudioRenderPreview
              ref={previewRef}
              file={previewFile}
              fov={renderFov}
              onReady={() => setPreviewReady(true)}
            />
            <label className="flex items-center gap-3 text-xs text-text-muted">
              <span className="shrink-0">Field of view: {renderFov}°</span>
              <input
                type="range"
                min={RENDER_FOV_MIN}
                max={RENDER_FOV_MAX}
                step={1}
                value={renderFov}
                onChange={(e) => {
                  const value = Number(e.target.value);
                  setRenderFov(value);
                  persistRenderSettings({ fov: value });
                }}
                className="flex-1 accent-primary"
                aria-label="Field of view"
              />
            </label>
          </>
        )}
        {step4Loading && (
          <p className="text-xs text-text-muted">Rendering in Blender — this usually takes 10–30 seconds...</p>
        )}
        {step4Image && (
          <div className="flex flex-col items-start gap-2">
            <img
              src={step4Image.url}
              alt="Studio render"
              className="max-h-80 rounded-lg border border-border-default"
            />
            <a href={step4Image.url} download={step4Image.filename} className={btnPillSm}>
              Download {step4Image.filename}
            </a>
          </div>
        )}
        {step4Error && (
          <p className="text-sm text-red-400">{step4Error}</p>
        )}
      </div>
    </div>
  );
}

export default ThreeDFileFinder;
