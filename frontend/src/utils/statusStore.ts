/**
 * Status Store — the single owner of all waiting-state UI (ADR 0002).
 *
 * Owns every Task and Pipeline in the app. Scope is strictly *waiting-state*
 * UI: spinners, progress bars, toasts, step statuses while the user waits.
 * It never touches feature inputs or outputs.
 *
 * Hand-rolled module store (no state library), matching the pattern that
 * StartupToasts established: module-level state + Set<listener> +
 * useSyncExternalStore. Every mutation replaces the containing array/object
 * so snapshots stay referentially stable between emissions.
 */

import { useSyncExternalStore } from "react";

export type TaskStatus = "pending" | "running" | "success" | "error";

export interface TaskProgress {
  current: number;
  total: number;
}

export interface Task {
  id: number;
  name: string;
  status: TaskStatus;
  progress?: TaskProgress;
  error?: string;
  /** Optional completion/failure message surfaced by the toast module. */
  message?: string;
  /** Optional long-form detail the toast module reveals on click. */
  detail?: string;
}

export interface Pipeline {
  id: number;
  name: string;
  steps: Task[];
  /** Index of the step currently running; -1 before start, steps.length after success. */
  currentIndex: number;
  status: TaskStatus;
  error?: string;
}

export interface TaskHandle {
  /** Report determinate progress. No-op after settle. */
  progress: (current: number) => void;
  /** Mark the task done; its toast auto-dismisses. */
  succeed: (message?: string, detail?: string) => void;
  /** Mark the task failed; its toast persists until dismissed. */
  fail: (error: string, detail?: string) => void;
}

export interface PipelineHandle {
  /** Report determinate progress on the current step. */
  progress: (current: number, total?: number) => void;
  /** Complete the current step and advance to the next one. */
  advance: () => void;
  /** Complete the current step and finish the whole pipeline. */
  succeed: (message?: string) => void;
  /** Fail the current step and the pipeline. */
  fail: (error: string) => void;
}

const SUCCESS_DISMISS_MS = 5000;

interface StoreState {
  tasks: Task[];
  pipelines: Pipeline[];
}

let state: StoreState = { tasks: [], pipelines: [] };
const listeners = new Set<() => void>();

function emit(): void {
  listeners.forEach((listener) => {
    try {
      listener();
    } catch (err) {
      console.warn("[status-store] listener threw:", err);
    }
  });
}

function nextId(): number {
  return Date.now() + Math.random();
}

function patchTask(id: number, patch: Partial<Task>): void {
  state = {
    ...state,
    tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)),
  };
  emit();
}

function patchPipeline(id: number, patch: Partial<Pipeline>): void {
  state = {
    ...state,
    pipelines: state.pipelines.map((p) => (p.id === id ? { ...p, ...patch } : p)),
  };
  emit();
}

function patchPipelineStep(
  pipelineId: number,
  stepIndex: number,
  patch: Partial<Task>,
): void {
  state = {
    ...state,
    pipelines: state.pipelines.map((p) =>
      p.id === pipelineId
        ? {
            ...p,
            steps: p.steps.map((s, i) => (i === stepIndex ? { ...s, ...patch } : s)),
          }
        : p,
    ),
  };
  emit();
}

/**
 * Internal escape hatch for the store's own UI modules (e.g. the toast
 * module's legacy update(label, message) API). Not part of the public
 * waiting-state API — feature code must use handles instead.
 */
export function __internalPatchTask(id: number, patch: Partial<Task>): void {
  try {
    patchTask(id, patch);
  } catch (err) {
    console.warn("[status-store] failed to patch task:", err);
  }
}

/** Remove a settled standalone task (used for auto-dismiss and manual dismiss). */
export function dismissTask(id: number): void {
  state = { ...state, tasks: state.tasks.filter((t) => t.id !== id) };
  emit();
}

/** Remove a settled pipeline (used for auto-dismiss and manual dismiss). */
export function dismissPipeline(id: number): void {
  state = { ...state, pipelines: state.pipelines.filter((p) => p.id !== id) };
  emit();
}

/**
 * Start a standalone task, returning its id alongside the handle. Used by the
 * store's own UI modules (toast module) that need the id for legacy update
 * APIs; feature code should use startTask.
 */
export function startTaskWithId(
  name: string,
  options?: { total?: number },
): { id: number; handle: TaskHandle } {
  const id = nextId();
  try {
    const task: Task = {
      id,
      name,
      status: "running",
      ...(options?.total !== undefined
        ? { progress: { current: 0, total: options.total } }
        : {}),
    };
    state = { ...state, tasks: [...state.tasks, task] };
    emit();
  } catch (err) {
    console.warn("[status-store] failed to start task:", err);
  }

  let settled = false;
  const handle: TaskHandle = {
    progress(current) {
      if (settled) return;
      try {
        const task = state.tasks.find((t) => t.id === id);
        if (!task?.progress) return;
        patchTask(id, { progress: { ...task.progress, current } });
      } catch (err) {
        console.warn("[status-store] failed to update task progress:", err);
      }
    },
    succeed(message, detail) {
      if (settled) return;
      settled = true;
      try {
        patchTask(id, { status: "success", message, detail });
        setTimeout(() => dismissTask(id), SUCCESS_DISMISS_MS);
      } catch (err) {
        console.warn("[status-store] failed to settle task:", err);
      }
    },
    fail(error, detail) {
      if (settled) return;
      settled = true;
      try {
        patchTask(id, { status: "error", error, message: error, detail });
      } catch (err) {
        console.warn("[status-store] failed to settle task:", err);
      }
    },
  };
  return { id, handle };
}

/**
 * Start a standalone task. Never throws — broken status UI must never break
 * the app. Concurrent tasks stack independently.
 */
export function startTask(name: string, options?: { total?: number }): TaskHandle {
  return startTaskWithId(name, options).handle;
}

/**
 * Start a pipeline: a named, ordered sequence of tasks. The first step begins
 * running immediately. Never throws.
 */
export function startPipeline(name: string, stepNames: string[]): PipelineHandle {
  const id = nextId();
  try {
    const steps: Task[] = stepNames.map((stepName, i) => ({
      id: nextId() + i,
      name: stepName,
      status: i === 0 ? "running" : "pending",
    }));
    const pipeline: Pipeline = {
      id,
      name,
      steps,
      currentIndex: steps.length > 0 ? 0 : -1,
      status: "running",
    };
    state = { ...state, pipelines: [...state.pipelines, pipeline] };
    emit();
  } catch (err) {
    console.warn("[status-store] failed to start pipeline:", err);
  }

  let settled = false;

  function currentIndex(): number {
    const p = state.pipelines.find((pl) => pl.id === id);
    return p ? p.currentIndex : -1;
  }

  return {
    progress(current, total) {
      if (settled) return;
      try {
        const idx = currentIndex();
        if (idx < 0) return;
        const p = state.pipelines.find((pl) => pl.id === id);
        if (!p) return;
        const step = p.steps[idx];
        const resolvedTotal = total ?? step.progress?.total;
        if (resolvedTotal === undefined) return;
        patchPipelineStep(id, idx, { progress: { current, total: resolvedTotal } });
      } catch (err) {
        console.warn("[status-store] failed to update pipeline progress:", err);
      }
    },
    advance() {
      if (settled) return;
      try {
        const idx = currentIndex();
        if (idx < 0) return;
        const p = state.pipelines.find((pl) => pl.id === id);
        if (!p) return;
        patchPipelineStep(id, idx, { status: "success" });
        const next = idx + 1;
        if (next < p.steps.length) {
          patchPipelineStep(id, next, { status: "running" });
          patchPipeline(id, { currentIndex: next });
        } else {
          // Advancing past the last step completes the pipeline.
          settled = true;
          patchPipeline(id, { currentIndex: p.steps.length, status: "success" });
          setTimeout(() => dismissPipeline(id), SUCCESS_DISMISS_MS);
        }
      } catch (err) {
        console.warn("[status-store] failed to advance pipeline:", err);
      }
    },
    succeed(message) {
      if (settled) return;
      settled = true;
      try {
        const idx = currentIndex();
        if (idx >= 0) {
          patchPipelineStep(id, idx, { status: "success", message });
        }
        const p = state.pipelines.find((pl) => pl.id === id);
        patchPipeline(id, {
          status: "success",
          currentIndex: p ? p.steps.length : 0,
        });
        setTimeout(() => dismissPipeline(id), SUCCESS_DISMISS_MS);
      } catch (err) {
        console.warn("[status-store] failed to settle pipeline:", err);
      }
    },
    fail(error) {
      if (settled) return;
      settled = true;
      try {
        const idx = currentIndex();
        if (idx >= 0) {
          patchPipelineStep(id, idx, { status: "error", error, message: error });
        }
        patchPipeline(id, { status: "error", error });
      } catch (err) {
        console.warn("[status-store] failed to settle pipeline:", err);
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

function getSnapshot(): StoreState {
  return state;
}

/** React binding: subscribe a component to the full store snapshot. */
export const statusStore = { subscribe, getSnapshot };

/**
 * React binding: derive a feature's waiting state from a task id held in a
 * ref/state. Returns true while that task is still pending/running in the
 * store, false once it settles (or if the id is null). Lets features drop
 * their local `is*` waiting booleans and read waiting state from the store.
 */
export function useTaskRunning(id: number | null): boolean {
  const { tasks } = useSyncExternalStore(subscribe, getSnapshot);
  if (id === null) return false;
  const task = tasks.find((t) => t.id === id);
  return task !== undefined && (task.status === "pending" || task.status === "running");
}

/**
 * React binding: true while any standalone task with the given name is still
 * running. Replaces feature-level `is*` booleans for single request/response
 * operations (sync, restock, bulk delete) — the operation's waiting state
 * lives in the store, not in a useState flag.
 */
export function useTaskRunningByName(name: string): boolean {
  const { tasks } = useSyncExternalStore(subscribe, getSnapshot);
  return tasks.some((t) => t.name === name && t.status === "running");
}
