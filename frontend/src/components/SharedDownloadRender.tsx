import { useEffect, useRef, useState } from "react";
import JSZip from "jszip";
import MessageBarInput from "./MessageBarInput";
import PipelineTracker from "./PipelineTracker";
import RenderProfileDropdown from "./RenderProfileDropdown";
import RenderProfileEditor from "./RenderProfileEditor";
import StudioRenderPreview, { type StudioRenderPreviewHandle } from "./StudioRenderPreview";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import { fetchWithProgress } from "../utils/fetchWithProgress";
import {
  dismissPipeline,
  startPipelineWithId,
  type PipelineHandle,
} from "../utils/statusStore";
import { DOWNLOAD_MODE_FILES, DOWNLOAD_MODE_FULL_ZIP, DOWNLOAD_MODE_SINGLE_FILE, type DownloadMode, type Pipeline, type MatchLabel } from "../constants/files3d";
import {
  DEFAULT_RENDER_SHOT_MODE,
  modelExtensionOf,
  NATIVE_RENDER_EXTENSIONS,
  RENDER_CANDIDATE_EXTENSIONS,
  RENDER_FOV_MAX,
  RENDER_FOV_MIN,
  RENDER_SETTINGS_DEFAULTS,
  RENDER_SETTINGS_SAVE_DEBOUNCE_MS,
  RENDERABLE_FORMATS_HINT,
  renderSettingsFromUnknown,
  type RenderFinish,
  type RenderProfileSettings,
  type RenderRigCamera,
  type RenderShotMode,
} from "../constants/render";

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

// True when a link is a supported downloadable pattern
const isDownloadSupported = (link: string) =>
  /thingiverse\.com\/thing[:/]\d+/.test(link) ||
  /printables\.com\/model\/\d+/.test(link) ||
  /makerworld\.com\/[^/]+\/models\/\d+/.test(link) ||
  /cults3d\.com\/[^/]+\/3d-model\/[^/]+\/[^/?#]+/.test(link);

// Metadata about the eBay listing + pipeline that produced the current Step 3
// URL — sent with the download request so the backend auto-saves a Saved 3D
// File record (ticket 09)
interface DownloadMeta {
  ebayUrl: string;
  ebayTitle: string;
  pipeline: Pipeline;
  matchLabel: MatchLabel;
}

interface SharedDownloadRenderProps {
  addToast?: (type: string, message: string) => void;
  fileDownloadDelay?: number;
  externalUrl?: string;
  externalMeta?: DownloadMeta | null;
  onExternalUrlConsumed?: () => void;
}

// Download + Render waiting state: one Pipeline in the Status Store per
// download (ADR 0002), rendered by PipelineTracker. The bespoke detail UIs
// (render progress text, preview, results) below are unchanged.
const DOWNLOAD_RENDER_STEPS = ["Download 3D file", "Studio render"];

function SharedDownloadRender({ addToast, fileDownloadDelay = 0, externalUrl, externalMeta, onExternalUrlConsumed }: SharedDownloadRenderProps) {
  // Step 3 — Download 3D File
  const [step3Url, setStep3Url] = useState("");
  const [step3LoadingMode, setStep3LoadingMode] = useState<DownloadMode | null>(null);
  const [step3Result, setStep3Result] = useState<{ filename: string; bytes: number; fileCount?: number } | null>(null);
  const [step3Error, setStep3Error] = useState<string | null>(null);
  // Listing/pipeline metadata attached to the current Step 3 URL (set when a
  // pipeline forwards a link; cleared on manual edits) — drives the auto-save
  const [step3Meta, setStep3Meta] = useState<DownloadMeta | null>(null);

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
  const [renderProgress, setRenderProgress] = useState<{ current: number; total: number; remainingSeconds: number | null; shot: number | null; shots: number | null } | null>(null);

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
  // Shot Mode + Camera Rig (Multi: N cameras → N images per Render click)
  const [renderShotMode, setRenderShotMode] = useState<RenderShotMode>(DEFAULT_RENDER_SHOT_MODE);
  const [renderRig, setRenderRig] = useState<RenderRigCamera[]>([]);
  // Multi-shot render results (N images); per-shot progress rides on renderProgress
  const [step4Images, setStep4Images] = useState<{ url: string; filename: string }[]>([]);
  const renderSettingsSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Step 4 — view switching: the profile dropdown or the Profile Editor
  const [step4View, setStep4View] = useState<"dropdown" | "editor">("dropdown");
  const [editingProfile, setEditingProfile] = useState<string | null | "create">(null);

  // Waiting state lives in the Status Store; only the pipeline id is local.
  const [pipelineId, setPipelineId] = useState<number | null>(null);
  const pipelineRef = useRef<PipelineHandle | null>(null);

  // Accept an external URL (from either pipeline) into the Step 3 input,
  // along with the listing/pipeline metadata for the download auto-save
  useEffect(() => {
    if (externalUrl) {
      setStep3Url(externalUrl);
      setStep3Meta(externalMeta ?? null);
      setStep3Result(null);
      setStep3Error(null);
      resetStep4();
      onExternalUrlConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalUrl]);

  // (Re)load the persisted flat Render Settings into local state; falls back to
  // spec defaults on failure. Used on mount and after the Profile Editor saves
  // "Current Settings" so Step 4 reflects the saved values.
  const reloadRenderSettings = () => {
    fetch("/api/render-settings")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        const parsed = renderSettingsFromUnknown(data);
        setRenderColor(parsed.color);
        setRenderRoughness(parsed.roughness);
        setRenderResolution(parsed.resolution);
        setRenderFov(parsed.fov);
        setRenderFinish(parsed.finish);
        setRenderLayerHeightMm(parsed.layer_height_mm);
        setRenderLayerDepth(parsed.layer_depth);
        setRenderKeyEnergy(parsed.key_energy);
        setRenderFillEnergy(parsed.fill_energy);
        setRenderRimEnergy(parsed.rim_energy);
        setRenderAmbient(parsed.ambient);
        setRenderShadow(parsed.shadow);
        setRenderShadowSoftness(parsed.shadow_softness);
        setRenderExposure(parsed.exposure);
        setRenderShotMode(parsed.shot_mode);
        setRenderRig(parsed.rig);
      })
      .catch(() => { /* keep spec defaults */ });
  };

  // Load persisted Render Settings once on mount; fall back to spec defaults on failure
  useEffect(() => {
    reloadRenderSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    const parsed = renderSettingsFromUnknown(settings);
    setRenderColor(parsed.color);
    setRenderRoughness(parsed.roughness);
    setRenderResolution(parsed.resolution);
    setRenderFov(parsed.fov);
    setRenderFinish(parsed.finish);
    setRenderLayerHeightMm(parsed.layer_height_mm);
    setRenderLayerDepth(parsed.layer_depth);
    setRenderKeyEnergy(parsed.key_energy);
    setRenderFillEnergy(parsed.fill_energy);
    setRenderRimEnergy(parsed.rim_energy);
    setRenderAmbient(parsed.ambient);
    setRenderShadow(parsed.shadow);
    setRenderShadowSoftness(parsed.shadow_softness);
    setRenderExposure(parsed.exposure);
    setRenderShotMode(parsed.shot_mode);
    setRenderRig(parsed.rig);
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

  // True when step3Url is a supported downloadable pattern
  const step3Supported = isDownloadSupported(step3Url.trim());

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleStep3Download = async (mode: DownloadMode) => {
    const link = step3Url.trim();
    if (!link || !step3Supported) return;
    setStep3LoadingMode(mode);
    setStep3Result(null);
    setStep3Error(null);
    resetStep4();
    if (pipelineId != null) dismissPipeline(pipelineId);
    const { id: newPipelineId, handle: pipeline } = startPipelineWithId(
      "Download + Render",
      DOWNLOAD_RENDER_STEPS,
    );
    pipelineRef.current = pipeline;
    setPipelineId(newPipelineId);
    try {
      // "files" mode reuses the full-zip response; unzipping happens client-side
      const wireMode = mode === DOWNLOAD_MODE_FILES ? DOWNLOAD_MODE_FULL_ZIP : mode;
      const res = await fetch("/api/download-3d-file", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          link,
          file_download_delay: fileDownloadDelay,
          mode: wireMode,
          // Pipeline metadata → backend auto-saves a Saved 3D File record
          ...(step3Meta && {
            ebay_listing_url: step3Meta.ebayUrl,
            ebay_listing_title: step3Meta.ebayTitle,
            pipeline: step3Meta.pipeline,
            match_label: step3Meta.matchLabel,
          }),
        }),
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
        if (savedToFolder === null) {
          pipeline.fail("Download cancelled");
          return; // user cancelled the folder picker
        }
        if (!savedToFolder) {
          downloadEntriesIndividually(entries);
          addToast?.("info", `Downloading ${entries.length} files individually — browser may ask to allow multiple downloads`);
        }
        setStep3Result({ filename: filename.replace(/\.zip$/i, ""), bytes: blob.size, fileCount: entries.length });
        pipeline.advance(); // → Studio render
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
      pipeline.advance(); // → Studio render
      if (step3Meta) addToast?.("success", "Saved to Saved 3D Files");
    } catch (err) {
      pipeline.fail((err as Error).message || "Download failed");
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
    setRenderProgress(null);
    setStep4Images([]);
    // Multi Shot Mode with a rig renders N cameras as one streaming job
    // (sequential backend Render Jobs); an empty rig falls back to the single
    // preview angle.
    const multi = renderShotMode === "multi" && renderRig.length > 0;
    try {
      const form = new FormData();
      form.append("file", renderFile);
      form.append("color", renderColor);
      form.append("roughness", String(renderRoughness));
      form.append("resolution", String(renderResolution));
      // Camera Intent: the angle the user framed in the preview (single mode;
      // in multi the rig's azimuth/elevation cameras take over)
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
      if (multi) {
        form.append("shot_mode", "multi");
        form.append("rig", JSON.stringify(renderRig));
      }
      const data = await fetchWithProgress(
        "/api/render",
        { method: "POST", body: form },
        (event) => {
          const shot = typeof event.shot === "number" ? event.shot : null;
          const shots = typeof event.shots === "number" ? event.shots : null;
          if (typeof event.current === "number" && typeof event.total === "number") {
            // Cycles checkpoint: sample N/M (tagged with the shot on multi runs)
            setRenderProgress({
              current: event.current,
              total: event.total,
              remainingSeconds: typeof event.remaining_seconds === "number" ? event.remaining_seconds : null,
              shot,
              shots,
            });
            pipelineRef.current?.progress(event.current, event.total);
          } else if (shot !== null) {
            // "shot i of N" marker: a new camera is starting (reset the sample bar)
            setRenderProgress({ current: 0, total: 0, remainingSeconds: null, shot, shots });
          }
        },
      ) as { image?: string; filename?: string; images?: string[] };
      const images = Array.isArray(data.images) && data.images.length > 0 ? data.images : (data.image ? [data.image] : []);
      if (images.length === 0 || !data.filename) throw new Error("Render finished without an image");
      if (multi) {
        setStep4Images(images.map((url) => ({ url, filename: url.split("/").pop() ?? "render.png" })));
      } else {
        setStep4Image({ url: images[0], filename: data.filename });
      }
      pipelineRef.current?.succeed();
    } catch (err) {
      pipelineRef.current?.fail((err as Error).message || "Render failed");
      setStep4Error((err as Error).message || "Render failed");
    } finally {
      setStep4Loading(false);
      setRenderProgress(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Waiting state: one Pipeline in the Status Store (ADR 0002) */}
      <PipelineTracker pipelineId={pipelineId} />

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
                setStep3Meta(null); // manual edit: no pipeline metadata to auto-save
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
            <span className="text-warning">Unsupported site</span>
          ) : (
            <span className="text-text-muted">Supported: printables.com, thingiverse.com, makerworld.com, cults3d.com (free only)</span>
          )}
        </p>
        {step3Result && (
          <p className="text-sm text-success">
            Downloaded: {step3Result.filename}{step3Result.fileCount !== undefined ? ` (${step3Result.fileCount} file${step3Result.fileCount !== 1 ? "s" : ""} unzipped)` : ""} ({formatBytes(step3Result.bytes)})
          </p>
        )}
        {step3Error && (
          <p className="text-sm text-danger">{step3Error}</p>
        )}
      </div>
      {/* Step 4 — Studio Render */}
      <div className="rounded-xl border border-border-default bg-surface-panel p-4 flex flex-col gap-3">
        <p className="text-sm font-semibold text-text-primary">Step 4 — Studio Render</p>
        {step4View === "editor" ? (
          <RenderProfileEditor
            editingProfile={editingProfile}
            onBack={() => setStep4View("dropdown")}
            onSavedCurrentSettings={reloadRenderSettings}
            addToast={addToast}
          />
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
          </div>
        )}
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
        {/* Multi-shot summary: the active profile's Camera Rig (angle list) */}
        {renderShotMode === "multi" && renderRig.length > 0 && (
          <p className="text-xs text-text-muted">
            <span className="font-semibold text-text-primary">Multi-shot: {renderRig.length} camera{renderRig.length !== 1 ? "s" : ""}</span>
            {" — "}
            {renderRig.map((c, i) => `#${i + 1} az ${c.azimuth}° el ${c.elevation}°`).join(", ")}
          </p>
        )}
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
          <div className="flex flex-col gap-1.5" role="status" aria-live="polite">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{
                  width: renderProgress && renderProgress.total > 0
                    ? `${Math.min(100, Math.round((renderProgress.current / renderProgress.total) * 100))}%`
                    : "5%",
                }}
              />
            </div>
            <p className="text-xs text-text-muted">
              {renderProgress
                ? `${renderProgress.shot != null && renderProgress.shots != null ? `Rendering shot ${renderProgress.shot} of ${renderProgress.shots} — ` : "Rendering — "}${renderProgress.total > 0 ? `sample ${renderProgress.current}/${renderProgress.total}${renderProgress.remainingSeconds != null ? `, ~${Math.ceil(renderProgress.remainingSeconds)}s remaining` : ""}` : "starting..."}`
                : "Rendering in Blender — this usually takes 10–30 seconds..."}
            </p>
          </div>
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
        {/* Multi-shot result: N-image grid with per-image download */}
        {step4Images.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {step4Images.map((image, index) => (
              <div key={image.url} className="flex flex-col items-start gap-1">
                <img
                  src={image.url}
                  alt={`Studio render shot ${index + 1}`}
                  className="w-full rounded-lg border border-border-default"
                />
                <a href={image.url} download={image.filename} className={btnPillSm}>
                  Download shot {index + 1}
                </a>
              </div>
            ))}
          </div>
        )}
        {step4Error && (
          <p className="text-sm text-danger">{step4Error}</p>
        )}
      </div>
    </div>
  );
}

export default SharedDownloadRender;
