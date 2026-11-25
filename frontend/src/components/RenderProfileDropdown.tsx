import { useEffect, useRef, useState } from "react";
import { btnPillSm } from "../styles/buttonPill";
import { CURRENT_SETTINGS_LABEL, type RenderProfilesResponse, type RenderProfileSettings } from "../constants/render";
import { toast } from "../utils/toasts";

interface RenderProfileDropdownProps {
  // Selecting a profile copies its settings into the flat settings; the parent
  // applies them to local state. Called with null for "Current Settings".
  onSelect: (name: string | null, settings: RenderProfileSettings | null) => void;
  // Edit navigates to the editor view (placeholder in ticket 04):
  // mode "edit" with a profile name, "edit-current" for Current Settings,
  // or "create" for a new profile.
  onEdit: (mode: "edit" | "edit-current" | "create", name: string | null) => void;
}

// Step 4's Render Profile picker: "Current Settings" (always present, the flat
// settings) plus every saved profile. The selection is sticky — the backend
// persists it as the active profile and this component restores it on load.
function RenderProfileDropdown({ onSelect, onEdit }: RenderProfileDropdownProps) {
  const [profiles, setProfiles] = useState<Record<string, RenderProfileSettings>>({});
  const [active, setActive] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  // Two-step inline delete confirm: holds the name awaiting confirmation
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  // Load profiles + the sticky active selection once on mount
  useEffect(() => {
    let cancelled = false;
    fetch("/api/render-profiles")
      .then((res) => (res.ok ? res.json() : null))
      .then((data: RenderProfilesResponse | null) => {
        if (cancelled || !data) return;
        setProfiles(data.profiles || {});
        setActive(data.active ?? null);
      })
      .catch(() => { /* keep empty list + Current Settings */ });
    return () => { cancelled = true; };
  }, []);

  // Close the dropdown on outside click / Escape
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const selectProfile = (name: string | null) => {
    setOpen(false);
    setConfirmDelete(null);
    setActive(name);
    const settings = name === null ? null : (profiles[name] ?? null);
    onSelect(name, settings);
    // Persist the sticky selection; "Current Settings" is active=null
    fetch("/api/render-profiles/active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }).catch(() => { /* selection still applies locally for this session */ });
  };

  const deleteProfile = (name: string) => {
    fetch(`/api/render-profiles/${encodeURIComponent(name)}`, { method: "DELETE" })
      .then(async (res) => {
        if (!res.ok) {
          const data = (await res.json().catch(() => null)) as { error?: string } | null;
          throw new Error(data?.error || `Could not delete "${name}"`);
        }
        const next = { ...profiles };
        delete next[name];
        setProfiles(next);
        setConfirmDelete(null);
        // Deleting the active profile falls back to "Current Settings" (the
        // backend also resets active to null; mirror that locally)
        if (active === name) {
          setActive(null);
          onSelect(null, null);
        }
        toast.info(`Deleted render profile "${name}"`);
      })
      .catch((err) => {
        setConfirmDelete(null);
        toast.error((err as Error).message || `Could not delete "${name}"`);
      });
  };

  const names = Object.keys(profiles).sort((a, b) => a.localeCompare(b));

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Render profile"
        onClick={() => { setOpen((v) => !v); setConfirmDelete(null); }}
        className="flex items-center gap-2 rounded border border-border-default bg-surface-panel px-2 py-1 text-sm text-text-primary hover:bg-surface-hover"
      >
        <span className="text-xs text-text-muted">Profile:</span>
        <span>{active ?? CURRENT_SETTINGS_LABEL}</span>
        <span aria-hidden="true" className="text-text-muted">▾</span>
      </button>
      {open && (
        <div
          role="listbox"
          aria-label="Render profiles"
          className="absolute z-20 mt-1 w-72 rounded-lg border border-border-default bg-surface-panel p-1 shadow-lg"
        >
          {/* Current Settings — the always-present default (active=null) */}
          <div
            role="option"
            aria-selected={active === null}
            className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
              active === null ? "bg-primary/10 text-text-primary" : "text-text-primary hover:bg-surface-hover"
            }`}
          >
            <button type="button" className="flex-1 text-left" onClick={() => selectProfile(null)}>
              {CURRENT_SETTINGS_LABEL}
            </button>
            <button type="button" className="text-xs text-text-muted hover:text-text-primary" onClick={() => { setOpen(false); onEdit("edit-current", null); }}>
              Edit
            </button>
          </div>
          {names.map((name) => (
            <div
              key={name}
              role="option"
              aria-selected={active === name}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                active === name ? "bg-primary/10 text-text-primary" : "text-text-primary hover:bg-surface-hover"
              }`}
            >
              {confirmDelete === name ? (
                <>
                  <span className="flex-1 text-xs text-text-muted">Delete "{name}"?</span>
                  <button type="button" className="text-xs text-red-400 hover:underline" onClick={() => deleteProfile(name)}>
                    Yes
                  </button>
                  <button type="button" className="text-xs text-text-muted hover:text-text-primary" onClick={() => setConfirmDelete(null)}>
                    No
                  </button>
                </>
              ) : (
                <>
                  <button type="button" className="flex-1 truncate text-left" title={name} onClick={() => selectProfile(name)}>
                    {name}
                  </button>
                  <button type="button" className="text-xs text-text-muted hover:text-text-primary" onClick={() => { setOpen(false); onEdit("edit", name); }}>
                    Edit
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete profile ${name}`}
                    className="text-xs text-text-muted hover:text-red-400"
                    onClick={() => setConfirmDelete(name)}
                  >
                    ✕
                  </button>
                </>
              )}
            </div>
          ))}
          <div className="mt-1 border-t border-border-default pt-1">
            <button
              type="button"
              className={`${btnPillSm} w-full`}
              onClick={() => { setOpen(false); onEdit("create", null); }}
            >
              + Create new profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default RenderProfileDropdown;
