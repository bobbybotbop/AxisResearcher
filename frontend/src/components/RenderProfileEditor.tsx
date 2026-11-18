import { useEffect, useRef, useState } from "react";
import StudioRenderPreview, { type StudioRenderPreviewHandle } from "./StudioRenderPreview";
import { btnPill, btnPillSm } from "../styles/buttonPill";
import {
  RENDER_AMBIENT_MAX,
  RENDER_ANGLE_PRESETS,
  RENDER_AZIMUTH_MAX,
  RENDER_AZIMUTH_MIN,
  RENDER_ELEVATION_MAX,
  RENDER_ELEVATION_MIN,
  RENDER_ENERGY_MAX,
  RENDER_EXPOSURE_MAX,
  RENDER_EXPOSURE_MIN,
  RENDER_FINISH_OPTIONS,
  RENDER_FOV_MAX,
  RENDER_FOV_MIN,
  RENDER_LAYER_HEIGHT_MM_MAX,
  RENDER_LAYER_HEIGHT_MM_MIN,
  RENDER_RESOLUTION_OPTIONS,
  RENDER_SHADOW_SOFTNESS_MAX,
  RENDER_SHADOW_SOFTNESS_MIN,
  RENDER_SHOT_MODE_OPTIONS,
  RENDER_STATUS_POLL_DEADLINE_MS,
  RENDER_STATUS_POLL_INTERVAL_MS,
  renderSettingsFromUnknown,
  type RenderFinish,
  type RenderProfileSettings,
  type RenderProfilesResponse,
  type RenderRigCamera,
  type RenderSettingsWire,
  type RenderShotMode,
} from "../constants/render";

// The Profile Editor (GLOSSARY.md): Step 4's in-place editor for Render
// Profiles. A square benchy viewer on the left, the full Render Settings
// surface on the right, a Render button that runs a real Blender Render Job on
// the bundled 3DBenchy with the editor's current values, and Save / "Save as
// new profile" buttons.
//
// The editor works on a LOCAL copy of the settings: sliders never persist
// directly (unlike the old inline row). Only Save writes — to the flat
// settings ("Current Settings"), to the named profile (edit mode), or to a new
// profile ("Save as new profile" → name modal → create).

// Which profile the editor opened for: a name (edit mode), null for "Current
// Settings", or "create" for a new profile starting from Current Settings.
export type EditingProfile = string | null | "create";

interface RenderProfileEditorProps {
  editingProfile: EditingProfile;
  onBack: () => void; // return to the profile dropdown view
  // Called after "Current Settings" is saved so the parent reloads the flat
  // settings into its own state (Step 4's render path reads them)
  onSavedCurrentSettings?: () => void;
  addToast?: (type: string, message: string) => void;
}

const BENCHY_URL = "/render/3DBenchy.stl";

function RenderProfileEditor({ editingProfile, onBack, onSavedCurrentSettings, addToast }: RenderProfileEditorProps) {
  // Local copy of the settings being edited — nothing persists until Save
  const [settings, setSettings] = useState<RenderSettingsWire>(() => renderSettingsFromUnknown({}));
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  const [benchyFile, setBenchyFile] = useState<File | null>(null);
  const [benchyError, setBenchyError] = useState<string | null>(null);
  const previewRef = useRef<StudioRenderPreviewHandle>(null);

  const [rendering, setRendering] = useState(false);
  const [renderImage, setRenderImage] = useState<{ url: string; filename: string } | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [nameModalOpen, setNameModalOpen] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");

  // Multi Shot Mode: which rig camera is selected (POV strip click / frustum
  // highlight / the camera the editor's Render button renders)
  const [selectedCamera, setSelectedCamera] = useState(0);

  const patch = (p: Partial<RenderSettingsWire>) => setSettings((s) => ({ ...s, ...p }));

  // Camera Rig editing (Multi Shot Mode): one-click preset adds, per-camera
  // azimuth/elevation numeric edits, remove. The rig is part of the profile's
  // settings — it round-trips through Save like every other field.
  const addRigCamera = (camera: RenderRigCamera) => {
    patch({ rig: [...settings.rig, { ...camera }] });
    setSelectedCamera(settings.rig.length);
  };
  const updateRigCamera = (index: number, p: Partial<RenderRigCamera>) => {
    patch({ rig: settings.rig.map((c, i) => (i === index ? { ...c, ...p } : c)) });
  };
  const removeRigCamera = (index: number) => {
    patch({ rig: settings.rig.filter((_, i) => i !== index) });
    setSelectedCamera((sel) => {
      if (settings.rig.length <= 1) return 0;
      if (index < sel) return sel - 1;
      if (index === sel) return Math.min(sel, settings.rig.length - 2);
      return sel;
    });
  };

  // Load initial values: "create"/null from the flat settings, a named profile
  // from the profiles API
  useEffect(() => {
    let cancelled = false;
    const apply = (data: RenderProfileSettings) => {
      if (cancelled) return;
      setSettings(renderSettingsFromUnknown(data));
      setSettingsLoaded(true);
    };
    if (editingProfile === "create" || editingProfile === null) {
      fetch("/api/render-settings")
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => apply(data ?? {}))
        .catch(() => apply({}));
    } else {
      fetch("/api/render-profiles")
        .then((res) => (res.ok ? res.json() : null))
        .then((data: RenderProfilesResponse | null) => apply(data?.profiles?.[editingProfile] ?? {}))
        .catch(() => apply({}));
    }
    return () => { cancelled = true; };
  }, [editingProfile]);

  // Preload the bundled benchy into the square viewer
  useEffect(() => {
    let cancelled = false;
    fetch(BENCHY_URL)
      .then((res) => {
        if (!res.ok) throw new Error("Could not load the bundled 3DBenchy");
        return res.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        setBenchyFile(new File([blob], "3DBenchy.stl"));
      })
      .catch((err) => {
        if (cancelled) return;
        setBenchyError((err as Error).message || "Could not load the bundled 3DBenchy");
      });
    return () => { cancelled = true; };
  }, []);

  // Render button: a real Blender Render Job on the benchy with the editor's
  // current values (same multipart POST + polling pattern as Step 4)
  const handleRender = async () => {
    if (!benchyFile || rendering) return;
    setRendering(true);
    setRenderError(null);
    setRenderImage(null);
    try {
      const form = new FormData();
      form.append("file", benchyFile);
      form.append("color", settings.color);
      form.append("roughness", String(settings.roughness));
      form.append("resolution", String(settings.resolution));
      const intent = previewRef.current?.getCameraIntent();
      if (intent) {
        form.append("camera_position", intent.position.join(","));
        form.append("camera_target", intent.target.join(","));
      }
      form.append("fov", String(settings.fov));
      form.append("finish", settings.finish);
      form.append("layer_height_mm", String(settings.layer_height_mm));
      form.append("layer_depth", String(settings.layer_depth));
      form.append("key_energy", String(settings.key_energy));
      form.append("fill_energy", String(settings.fill_energy));
      form.append("rim_energy", String(settings.rim_energy));
      form.append("ambient", String(settings.ambient));
      form.append("shadow", String(settings.shadow));
      form.append("shadow_softness", String(settings.shadow_softness));
      form.append("exposure", String(settings.exposure));
      // Shot Mode: Multi renders the SELECTED rig camera only (one job — the
      // full rig runs from the main Step 4 panel). The backend auto-frames
      // distance/look-at, so the rig camera goes as azimuth/elevation.
      if (settings.shot_mode === "multi") {
        const camera = settings.rig[Math.min(selectedCamera, settings.rig.length - 1)];
        if (camera) {
          form.append("shot_mode", "multi");
          form.append("rig", JSON.stringify([camera]));
        }
      }
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
          setRenderImage({ url: status.image, filename: status.filename });
          break;
        }
        if (status.status === "failed") throw new Error(status.error || "Render failed");
        if (Date.now() > deadline) throw new Error("Render is taking too long — check that Blender is installed and the backend is running");
      }
    } catch (err) {
      setRenderError((err as Error).message || "Render failed");
    } finally {
      setRendering(false);
    }
  };

  // Save: "Current Settings" → flat settings; a named profile → overwrite in
  // place; "create" → the name modal → create
  const handleSave = async () => {
    if (saving) return;
    if (editingProfile === "create") {
      setNewProfileName("");
      setNameModalOpen(true);
      return;
    }
    setSaving(true);
    try {
      if (editingProfile === null) {
        const res = await fetch("/api/render-settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(settings),
        });
        if (!res.ok) {
          const data = (await res.json().catch(() => null)) as { error?: string } | null;
          throw new Error(data?.error || "Could not save the settings");
        }
        addToast?.("info", "Saved Current Settings");
        onSavedCurrentSettings?.();
      } else {
        const res = await fetch(`/api/render-profiles/${encodeURIComponent(editingProfile)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ settings }),
        });
        if (!res.ok) {
          const data = (await res.json().catch(() => null)) as { error?: string } | null;
          throw new Error(data?.error || `Could not save "${editingProfile}"`);
        }
        addToast?.("info", `Saved render profile "${editingProfile}"`);
      }
      onBack();
    } catch (err) {
      addToast?.("error", (err as Error).message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleCreateProfile = async () => {
    const name = newProfileName.trim();
    if (!name || saving) return;
    setSaving(true);
    try {
      const res = await fetch("/api/render-profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, settings }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        throw new Error(data?.error || `Could not create "${name}"`);
      }
      setNameModalOpen(false);
      addToast?.("info", `Created render profile "${name}"`);
      onBack();
    } catch (err) {
      addToast?.("error", (err as Error).message || "Create failed");
    } finally {
      setSaving(false);
    }
  };

  const title =
    editingProfile === "create"
      ? "Create new profile"
      : editingProfile === null
        ? "Edit Current Settings"
        : `Edit profile: ${editingProfile}`;

  const sliderClass = "w-full accent-primary";
  const selectClass = "rounded border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary";

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border-default p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-text-primary">{title}</p>
        <button type="button" className={btnPillSm} onClick={onBack}>
          ← Back to profiles
        </button>
      </div>
      <div className="flex flex-col gap-4 md:flex-row">
        {/* Square benchy viewer + render result. Multi Shot Mode turns it into
            the Rig Overview (wireframe frustums + sight lines) with a POV strip. */}
        <div className="flex w-full flex-col gap-2 md:w-1/2">
          {benchyFile ? (
            <StudioRenderPreview
              ref={previewRef}
              file={benchyFile}
              fov={settings.fov}
              square
              rig={settings.shot_mode === "multi" ? settings.rig : undefined}
              selectedCamera={selectedCamera}
            />
          ) : (
            <div className="flex aspect-square w-full items-center justify-center rounded-lg border border-border-default bg-surface-panel">
              <p className="text-xs text-text-muted">{benchyError ?? "Loading 3DBenchy..."}</p>
            </div>
          )}
          {/* POV strip: one small square thumbnail per rig camera, each a
              lightweight render from that camera's POV. Click selects the
              camera (highlights its frustum in the overview). */}
          {settings.shot_mode === "multi" && benchyFile && settings.rig.length > 0 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {settings.rig.map((camera, index) => (
                <button
                  key={index}
                  type="button"
                  aria-label={`Select camera ${index + 1} (azimuth ${camera.azimuth}°, elevation ${camera.elevation}°)`}
                  aria-pressed={selectedCamera === index}
                  onClick={() => setSelectedCamera(index)}
                  className={`w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-colors ${
                    selectedCamera === index
                      ? "border-primary ring-2 ring-primary/30"
                      : "border-border-default hover:border-primary/50"
                  }`}
                >
                  <StudioRenderPreview file={benchyFile} fov={settings.fov} square fixedCamera={camera} hideHint />
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-3">
            <button
              type="button"
              className={btnPill}
              onClick={handleRender}
              disabled={!benchyFile || rendering}
            >
              {rendering ? "Rendering..." : "Render"}
            </button>
            {rendering && (
              <p className="text-xs text-text-muted">Rendering in Blender — this usually takes 10–30 seconds...</p>
            )}
          </div>
          {renderImage && (
            <div className="flex flex-col items-start gap-2">
              <img
                src={renderImage.url}
                alt="Benchy render with the editor's settings"
                className="w-full rounded-lg border border-border-default"
              />
              <a href={renderImage.url} download={renderImage.filename} className={btnPillSm}>
                Download {renderImage.filename}
              </a>
            </div>
          )}
          {renderError && <p className="text-sm text-red-400">{renderError}</p>}
        </div>
        {/* Settings panel — local copy; only Save persists */}
        <div className="flex w-full flex-col gap-3 md:w-1/2" aria-busy={!settingsLoaded}>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Color</span>
            <input
              type="color"
              aria-label="Color"
              value={settings.color}
              onChange={(e) => patch({ color: e.target.value })}
              className="h-8 w-16 cursor-pointer rounded border border-border-default bg-surface-panel"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Glossiness ({(1 - settings.roughness).toFixed(2)})</span>
            {/* Slider shows glossiness; the persisted/wire value is Principled
                roughness (glossiness = 1 − roughness), so dragging up = glossier */}
            <input
              type="range"
              aria-label="Glossiness"
              min={0}
              max={1}
              step={0.05}
              value={1 - settings.roughness}
              onChange={(e) => patch({ roughness: 1 - Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Finish</span>
            <select
              aria-label="Surface finish"
              value={settings.finish}
              onChange={(e) => patch({ finish: e.target.value as RenderFinish })}
              className={selectClass}
            >
              {RENDER_FINISH_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          {settings.finish === "layer-lines" && (
            <>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-text-muted">Layer height ({settings.layer_height_mm.toFixed(2)}mm)</span>
                <input
                  type="range"
                  aria-label="Layer height"
                  min={RENDER_LAYER_HEIGHT_MM_MIN}
                  max={RENDER_LAYER_HEIGHT_MM_MAX}
                  step={0.01}
                  value={settings.layer_height_mm}
                  onChange={(e) => patch({ layer_height_mm: Number(e.target.value) })}
                  className={sliderClass}
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs text-text-muted">Line depth ({settings.layer_depth.toFixed(2)})</span>
                <input
                  type="range"
                  aria-label="Line depth"
                  min={0}
                  max={1}
                  step={0.05}
                  value={settings.layer_depth}
                  onChange={(e) => patch({ layer_depth: Number(e.target.value) })}
                  className={sliderClass}
                />
              </label>
            </>
          )}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Key light ({settings.key_energy})</span>
            <input
              type="range"
              aria-label="Key light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={settings.key_energy}
              onChange={(e) => patch({ key_energy: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Fill light ({settings.fill_energy})</span>
            <input
              type="range"
              aria-label="Fill light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={settings.fill_energy}
              onChange={(e) => patch({ fill_energy: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Rim light ({settings.rim_energy})</span>
            <input
              type="range"
              aria-label="Rim light intensity"
              min={0}
              max={RENDER_ENERGY_MAX}
              step={10}
              value={settings.rim_energy}
              onChange={(e) => patch({ rim_energy: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Ambient ({settings.ambient.toFixed(2)})</span>
            <input
              type="range"
              aria-label="Ambient strength"
              min={0}
              max={RENDER_AMBIENT_MAX}
              step={0.05}
              value={settings.ambient}
              onChange={(e) => patch({ ambient: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Exposure ({settings.exposure.toFixed(2)})</span>
            <input
              type="range"
              aria-label="Exposure"
              min={RENDER_EXPOSURE_MIN}
              max={RENDER_EXPOSURE_MAX}
              step={0.05}
              value={settings.exposure}
              onChange={(e) => patch({ exposure: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          <label className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Shadow</span>
            <input
              type="checkbox"
              aria-label="Shadow"
              checked={settings.shadow}
              onChange={(e) => patch({ shadow: e.target.checked })}
              className="h-5 w-5 accent-primary"
            />
          </label>
          {settings.shadow && (
            <label className="flex flex-col gap-1">
              <span className="text-xs text-text-muted">Shadow softness ({settings.shadow_softness.toFixed(1)})</span>
              <input
                type="range"
                aria-label="Shadow softness"
                min={RENDER_SHADOW_SOFTNESS_MIN}
                max={RENDER_SHADOW_SOFTNESS_MAX}
                step={0.1}
                value={settings.shadow_softness}
                onChange={(e) => patch({ shadow_softness: Number(e.target.value) })}
                className={sliderClass}
              />
            </label>
          )}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Resolution</span>
            <select
              aria-label="Resolution"
              value={settings.resolution}
              onChange={(e) => patch({ resolution: Number(e.target.value) })}
              className={selectClass}
            >
              {RENDER_RESOLUTION_OPTIONS.map((size) => (
                <option key={size} value={size}>{size} × {size}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Field of view ({settings.fov}°)</span>
            <input
              type="range"
              aria-label="Field of view"
              min={RENDER_FOV_MIN}
              max={RENDER_FOV_MAX}
              step={1}
              value={settings.fov}
              onChange={(e) => patch({ fov: Number(e.target.value) })}
              className={sliderClass}
            />
          </label>
          {/* Shot Mode (GLOSSARY): Single captures the angle from the preview;
              Multi reveals the Camera Rig — the Rig Overview above plus the
              preset library and per-camera editing below. */}
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">Shot Mode</span>
            <select
              aria-label="Shot Mode"
              value={settings.shot_mode}
              onChange={(e) => patch({ shot_mode: e.target.value as RenderShotMode })}
              className={selectClass}
            >
              {RENDER_SHOT_MODE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          {settings.shot_mode === "multi" && (
            <div className="flex flex-col gap-2 rounded-lg border border-border-default p-2">
              <p className="text-xs font-semibold text-text-primary">Camera Rig ({settings.rig.length} camera{settings.rig.length !== 1 ? "s" : ""})</p>
              {/* Preset library: one-click adds */}
              <div className="flex flex-wrap gap-1">
                {Object.entries(RENDER_ANGLE_PRESETS).map(([name, camera]) => (
                  <button
                    key={name}
                    type="button"
                    className={btnPillSm}
                    onClick={() => addRigCamera(camera)}
                  >
                    + {name}
                  </button>
                ))}
              </div>
              {/* Per-camera azimuth/elevation editing + remove */}
              {settings.rig.length === 0 ? (
                <p className="text-xs text-text-muted">Add cameras from the presets above — Render in Multi renders the selected camera.</p>
              ) : (
                <ol className="flex flex-col gap-2">
                  {settings.rig.map((camera, index) => (
                    <li
                      key={index}
                      className={`flex items-center gap-2 rounded-md border p-2 ${
                        selectedCamera === index ? "border-primary bg-primary/5" : "border-border-default"
                      }`}
                    >
                      <button
                        type="button"
                        aria-label={`Select camera ${index + 1}`}
                        onClick={() => setSelectedCamera(index)}
                        className="w-5 shrink-0 text-right text-sm font-bold text-text-muted hover:text-text-primary"
                      >
                        {index + 1}.
                      </button>
                      <label className="flex items-center gap-1 text-xs text-text-muted">
                        Az
                        <input
                          type="number"
                          aria-label={`Camera ${index + 1} azimuth`}
                          min={RENDER_AZIMUTH_MIN}
                          max={RENDER_AZIMUTH_MAX}
                          step={1}
                          value={camera.azimuth}
                          onChange={(e) => updateRigCamera(index, { azimuth: Number(e.target.value) })}
                          className="w-16 rounded border border-border-default bg-surface-panel px-1 py-0.5 text-xs text-text-primary"
                        />
                      </label>
                      <label className="flex items-center gap-1 text-xs text-text-muted">
                        El
                        <input
                          type="number"
                          aria-label={`Camera ${index + 1} elevation`}
                          min={RENDER_ELEVATION_MIN}
                          max={RENDER_ELEVATION_MAX}
                          step={1}
                          value={camera.elevation}
                          onChange={(e) => updateRigCamera(index, { elevation: Number(e.target.value) })}
                          className="w-16 rounded border border-border-default bg-surface-panel px-1 py-0.5 text-xs text-text-primary"
                        />
                      </label>
                      <button
                        type="button"
                        aria-label={`Remove camera ${index + 1}`}
                        onClick={() => removeRigCamera(index)}
                        className="ml-auto text-xs text-text-muted hover:text-red-400"
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
          <div className="mt-1 flex items-center gap-3 border-t border-border-default pt-3">
            <button type="button" className={btnPill} onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : editingProfile === "create" ? "Save as new profile" : "Save"}
            </button>
            {editingProfile !== "create" && (
              <button
                type="button"
                className={btnPillSm}
                onClick={() => { setNewProfileName(""); setNameModalOpen(true); }}
                disabled={saving}
              >
                Save as new profile
              </button>
            )}
          </div>
        </div>
      </div>
      {/* Save-as-new name modal */}
      {nameModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setNameModalOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-name-modal-title"
        >
          <div
            className="flex w-full max-w-sm flex-col gap-3 rounded-xl border border-border-default bg-surface-panel p-4 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <p id="profile-name-modal-title" className="text-sm font-semibold text-text-primary">
              Save as new profile
            </p>
            <form
              onSubmit={(e) => { e.preventDefault(); handleCreateProfile(); }}
              className="flex flex-col gap-3"
            >
              <input
                type="text"
                aria-label="Profile name"
                placeholder="Profile name..."
                value={newProfileName}
                onChange={(e) => setNewProfileName(e.target.value)}
                autoFocus
                className="rounded border border-border-default bg-surface-panel px-3 py-2 text-sm text-text-primary"
              />
              <div className="flex items-center justify-end gap-2">
                <button type="button" className={btnPillSm} onClick={() => setNameModalOpen(false)} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" className={btnPillSm} disabled={!newProfileName.trim() || saving}>
                  {saving ? "Saving..." : "Save profile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default RenderProfileEditor;
