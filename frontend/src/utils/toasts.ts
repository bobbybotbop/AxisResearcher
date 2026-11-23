/**
 * Standalone toast module (ADR 0003) — the app's single non-blocking toast
 * channel, decoupled from the Status Store. Owns its own hand-rolled module
 * store (module state + Set<listener> + useSyncExternalStore-compatible
 * subscribe/getSnapshot); StartupToasts renders the snapshot.
 *
 * Direct-call API:
 *   toast.error(msg)   — persists until manually dismissed
 *   toast.success(msg) — auto-dismisses after ~5s
 *   toast.info(msg)    — success semantics
 *   startTaskToast(label) — handle for a pending task that settles later
 *
 * Never throws — a broken toast must never break the app.
 */

export type ToastStatus = "pending" | "success" | "error";

export interface ToastItem {
  id: number;
  /** Primary one-line label. */
  title: string;
  status: ToastStatus;
  /** Optional secondary line under the title. */
  message?: string;
  /** Optional long-form detail the toast reveals on click. */
  detail?: string;
}

export interface TaskToastHandle {
  /** Update the pending toast's label (and optional message) in place. */
  update: (label: string, message?: string) => void;
  /** Mark the task done; toast auto-dismisses after ~5s. */
  succeed: (message?: string) => void;
  /** Mark the task failed; toast persists until manually dismissed. */
  fail: (message: string, detail?: string) => void;
}

const SUCCESS_DISMISS_MS = 5000;

interface ToastState {
  toasts: ToastItem[];
}

let state: ToastState = { toasts: [] };
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch (err) {
      console.warn("[toasts] listener threw:", err);
    }
  });
}

function nextId(): number {
  return Date.now() + Math.random();
}

function patchToast(id: number, patch: Partial<ToastItem>): void {
  state = {
    ...state,
    toasts: state.toasts.map((t) => (t.id === id ? { ...t, ...patch } : t)),
  };
  emit();
}

function addToast(toastItem: ToastItem): void {
  state = { ...state, toasts: [...state.toasts, toastItem] };
  emit();
}

/** Remove a toast (used for auto-dismiss and manual dismiss). */
export function dismissToast(id: number): void {
  try {
    state = { ...state, toasts: state.toasts.filter((t) => t.id !== id) };
    emit();
  } catch (err) {
    console.warn("[toasts] failed to dismiss toast:", err);
  }
}

/**
 * Start a pending toast for a longer-running task, returning a handle to
 * update and settle it. Concurrent toasts stack independently. Never throws.
 */
export function startTaskToast(label: string): TaskToastHandle {
  const id = nextId();
  try {
    addToast({ id, title: label, status: "pending" });
  } catch (err) {
    console.warn("[toasts] failed to start toast:", err);
  }

  let settled = false;
  return {
    update(nextLabel, message) {
      if (settled) return;
      try {
        patchToast(id, { title: nextLabel, message });
      } catch (err) {
        console.warn("[toasts] failed to update toast:", err);
      }
    },
    succeed(message) {
      if (settled) return;
      settled = true;
      try {
        patchToast(id, { status: "success", message });
        setTimeout(() => dismissToast(id), SUCCESS_DISMISS_MS);
      } catch (err) {
        console.warn("[toasts] failed to settle toast:", err);
      }
    },
    fail(message, detail) {
      if (settled) return;
      settled = true;
      try {
        patchToast(id, { status: "error", message, detail });
      } catch (err) {
        console.warn("[toasts] failed to settle toast:", err);
      }
    },
  };
}

function fireToast(kind: "success" | "error", message: string, detail?: string): void {
  try {
    const id = nextId();
    addToast({ id, title: message, status: kind, detail });
    if (kind === "success") {
      setTimeout(() => dismissToast(id), SUCCESS_DISMISS_MS);
    }
  } catch (err) {
    console.warn("[toasts] failed to fire toast:", err);
  }
}

/**
 * Fire-and-forget one-shot toasts. For the common case where a feature just
 * wants to tell the user something happened — no pending phase, no progress.
 * `info` maps to success semantics deliberately.
 */
export const toast = {
  success(message: string, detail?: string): void {
    fireToast("success", message, detail);
  },
  info(message: string, detail?: string): void {
    fireToast("success", message, detail);
  },
  error(message: string, detail?: string): void {
    fireToast("error", message, detail);
  },
};

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): ToastState {
  return state;
}

/** React binding: subscribe a component to the toast snapshot. */
export const toastStore = { subscribe, getSnapshot };
