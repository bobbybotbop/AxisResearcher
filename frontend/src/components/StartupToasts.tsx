import { useSyncExternalStore } from "react";
import ReactDOM from "react-dom";
import {
  __internalPatchTask,
  dismissTask,
  startTaskWithId,
  statusStore,
  type Task,
} from "../utils/statusStore";

export type StartupToastStatus = "pending" | "success" | "error";

export interface TaskToastHandle {
  /** Update the pending toast's label (and optional message) in place. */
  update: (label: string, message?: string) => void;
  /** Mark the task done; toast auto-dismisses after ~5s. */
  succeed: (message?: string) => void;
  /** Mark the task failed; toast persists until manually dismissed. */
  fail: (message: string) => void;
}

/**
 * Backwards-compatible wrapper over the Status Store's startTask. Existing
 * callers (eBay quantity refresh, token refresh) keep working unchanged.
 * Never throws — a broken toast must never break the app.
 */
export function startTaskToast(label: string): TaskToastHandle {
  const { id, handle } = startTaskWithId(label);
  return {
    update(nextLabel, message) {
      __internalPatchTask(id, { name: nextLabel, message });
    },
    succeed: handle.succeed,
    fail: handle.fail,
  };
}

export function dismissTaskToast(id: number): void {
  dismissTask(id);
}

interface StartupToastItemProps {
  task: Task;
  onDismiss: (id: number) => void;
}

function StartupToastItem({ task, onDismiss }: StartupToastItemProps) {
  const status: StartupToastStatus =
    task.status === "success"
      ? "success"
      : task.status === "error"
        ? "error"
        : "pending";

  const palette =
    status === "success"
      ? "bg-success text-white"
      : status === "error"
        ? "bg-danger text-white"
        : "border border-border-default bg-surface-panel text-text-primary";

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg ${palette}`}
      style={{ minWidth: "280px", maxWidth: "480px" }}
      role={status === "error" ? "alert" : "status"}
    >
      {status === "pending" ? (
        <span
          className="mt-0.5 h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-text-muted/40 border-t-primary"
          aria-hidden="true"
        />
      ) : (
        <span className="mt-0.5 shrink-0 text-sm font-bold" aria-hidden="true">
          {status === "success" ? "✓" : "✕"}
        </span>
      )}
      <div className="flex-1">
        <p className="text-sm font-medium leading-snug">{task.name}</p>
        {task.message && (
          <p className={`mt-0.5 text-xs ${status === "pending" ? "text-text-muted" : "opacity-80"}`}>
            {task.message}
          </p>
        )}
        {task.progress && status === "pending" && (
          <p className="mt-0.5 text-xs text-text-muted">
            {task.progress.current} of {task.progress.total}
          </p>
        )}
      </div>
      {status !== "pending" && (
        <button
          type="button"
          onClick={() => onDismiss(task.id)}
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
 * The Status Store's toast module. Renders standalone tasks as stacked,
 * non-blocking toasts fixed to the bottom-right corner; the container ignores
 * pointer events so the app stays usable while tasks run. Success toasts
 * auto-dismiss; error toasts persist until manually dismissed.
 */
export default function StartupToasts() {
  const { tasks } = useSyncExternalStore(statusStore.subscribe, statusStore.getSnapshot);
  if (tasks.length === 0) return null;
  return ReactDOM.createPortal(
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[9999] flex flex-col items-end gap-2"
      role="region"
      aria-label="Background task notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      {tasks.map((task) => (
        <StartupToastItem key={task.id} task={task} onDismiss={dismissTaskToast} />
      ))}
    </div>,
    document.body,
  );
}
