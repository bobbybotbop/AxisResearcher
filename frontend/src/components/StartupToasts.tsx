import { useState, useSyncExternalStore } from "react";
import ReactDOM from "react-dom";
import { dismissToast, toastStore, type ToastItem } from "../utils/toasts";

function StartupToastItem({ toast: t, onDismiss }: { toast: ToastItem; onDismiss: (id: number) => void }) {
  const [detailOpen, setDetailOpen] = useState(false);

  const palette =
    t.status === "success"
      ? "bg-success text-white"
      : t.status === "error"
        ? "bg-danger text-white"
        : "border border-border-default bg-surface-panel text-text-primary";

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg ${palette}`}
      style={{ minWidth: "280px", maxWidth: "480px" }}
      role={t.status === "error" ? "alert" : "status"}
    >
      {t.status === "pending" ? (
        <span
          className="mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-text-muted/40 border-t-primary"
          aria-hidden="true"
        />
      ) : (
        <span className="mt-0.5 shrink-0 text-sm font-bold" aria-hidden="true">
          {t.status === "success" ? "✓" : "✕"}
        </span>
      )}
      <div className="flex-1">
        <p className="text-sm font-medium leading-snug">{t.title}</p>
        {t.message && (
          <p className={`mt-0.5 text-xs ${t.status === "pending" ? "text-text-muted" : "opacity-80"}`}>
            {t.message}
          </p>
        )}
        {t.detail && t.status !== "pending" && (
          <>
            <button
              type="button"
              onClick={() => setDetailOpen((o) => !o)}
              className="mt-0.5 text-xs underline opacity-80 hover:opacity-100"
              aria-expanded={detailOpen}
            >
              {detailOpen ? "Hide details" : "Details"}
            </button>
            {detailOpen && (
              <p className="mt-1 whitespace-pre-line text-xs opacity-80">
                {t.detail}
              </p>
            )}
          </>
        )}
      </div>
      {t.status !== "pending" && (
        <button
          type="button"
          onClick={() => onDismiss(t.id)}
          className="ml-1 shrink-0 text-sm opacity-60 hover:opacity-100"
          aria-label="Dismiss"
        >
          ×
        </button>
      )}
    </div>
  );
}

/**
 * The app's toast module. Renders stacked, non-blocking toasts fixed to the
 * bottom-right corner; the container ignores pointer events so the app stays
 * usable while tasks run. Success toasts auto-dismiss; error toasts persist
 * until manually dismissed.
 *
 * Renders the standalone toast module's snapshot (`utils/toasts`), which
 * feature code calls directly via `toast.error(...)` / `startTaskToast(...)`.
 */
export default function StartupToasts() {
  const { toasts } = useSyncExternalStore(toastStore.subscribe, toastStore.getSnapshot);
  if (toasts.length === 0) return null;
  return ReactDOM.createPortal(
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[9999] flex flex-col items-end gap-2"
      role="region"
      aria-label="Background task notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      {toasts.map((t) => (
        <StartupToastItem key={t.id} toast={t} onDismiss={dismissToast} />
      ))}
    </div>,
    document.body,
  );
}
