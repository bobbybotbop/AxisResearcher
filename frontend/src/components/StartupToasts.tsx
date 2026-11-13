import { useSyncExternalStore } from "react";
import ReactDOM from "react-dom";

export type StartupToastStatus = "pending" | "success" | "error";

interface StartupToast {
  id: number;
  status: StartupToastStatus;
  label: string;
  message?: string;
}

export interface TaskToastHandle {
  /** Mark the task done; toast auto-dismisses after ~5s. */
  succeed: (message?: string) => void;
  /** Mark the task failed; toast persists until manually dismissed. */
  fail: (message: string) => void;
}

const SUCCESS_DISMISS_MS = 5000;

// Module-level store so startup tasks can raise toasts from anywhere without
// prop drilling. Every mutation replaces the array so useSyncExternalStore
// snapshots stay referentially stable between emissions.
let toasts: StartupToast[] = [];
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch (err) {
      console.warn("[startup-toasts] listener threw:", err);
    }
  });
}

function updateToast(id: number, patch: Partial<StartupToast>): void {
  toasts = toasts.map((t) => (t.id === id ? { ...t, ...patch } : t));
  emit();
}

export function dismissTaskToast(id: number): void {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

/**
 * Raise a pending toast for a background task. Never throws — a broken toast
 * must never break the app. Concurrent calls stack independently.
 */
export function startTaskToast(label: string): TaskToastHandle {
  const id = Date.now() + Math.random();
  try {
    toasts = [...toasts, { id, status: "pending", label }];
    emit();
  } catch (err) {
    console.warn("[startup-toasts] failed to start toast:", err);
  }

  let settled = false;
  return {
    succeed(message) {
      if (settled) return;
      settled = true;
      try {
        updateToast(id, { status: "success", message });
        setTimeout(() => dismissTaskToast(id), SUCCESS_DISMISS_MS);
      } catch (err) {
        console.warn("[startup-toasts] failed to settle toast:", err);
      }
    },
    fail(message) {
      if (settled) return;
      settled = true;
      try {
        updateToast(id, { status: "error", message });
      } catch (err) {
        console.warn("[startup-toasts] failed to settle toast:", err);
      }
    },
  };
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): StartupToast[] {
  return toasts;
}

interface StartupToastItemProps {
  toast: StartupToast;
  onDismiss: (id: number) => void;
}

function StartupToastItem({ toast, onDismiss }: StartupToastItemProps) {
  const palette =
    toast.status === "success"
      ? "bg-success text-white"
      : toast.status === "error"
        ? "bg-danger text-white"
        : "border border-border-default bg-surface-panel text-text-primary";

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg ${palette}`}
      style={{ minWidth: "280px", maxWidth: "480px" }}
      role={toast.status === "error" ? "alert" : "status"}
    >
      {toast.status === "pending" ? (
        <span
          className="mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-text-muted/40 border-t-primary"
          aria-hidden="true"
        />
      ) : (
        <span className="mt-0.5 shrink-0 text-sm font-bold" aria-hidden="true">
          {toast.status === "success" ? "✓" : "✕"}
        </span>
      )}
      <div className="flex-1">
        <p className="text-sm font-medium leading-snug">{toast.label}</p>
        {toast.message && (
          <p className={`mt-0.5 text-xs ${toast.status === "pending" ? "text-text-muted" : "opacity-80"}`}>
            {toast.message}
          </p>
        )}
      </div>
      {toast.status !== "pending" && (
        <button
          type="button"
          onClick={() => onDismiss(toast.id)}
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
 * Stacked, non-blocking toasts for background startup tasks (eBay startup
 * sync, quantity refresh). Fixed to the bottom-right corner; the container
 * ignores pointer events so the app stays usable while tasks run.
 */
export default function StartupToasts() {
  const items = useSyncExternalStore(subscribe, getSnapshot);
  if (items.length === 0) return null;
  return ReactDOM.createPortal(
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[9999] flex flex-col items-end gap-2"
      role="region"
      aria-label="Background task notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      {items.map((toast) => (
        <StartupToastItem key={toast.id} toast={toast} onDismiss={dismissTaskToast} />
      ))}
    </div>,
    document.body,
  );
}
