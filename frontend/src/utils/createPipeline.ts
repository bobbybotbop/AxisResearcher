import type { StepProgress, StepState } from "../components/StepCard";

/**
 * Create workflow step state (ADR 0003). The Create flow — fetch listing →
 * initial JSON → categorize → bg removal → image generation → text
 * generation → create listing — owns its waiting state in the workflow
 * component's local useState; these pure helpers are the state machine. No
 * Status Store, no PipelineTracker.
 */

export type CreateStepId =
  | "fetch"
  | "json"
  | "categorize"
  | "bgRemoval"
  | "imageGen"
  | "textGen"
  | "createListing";

export interface CreateStepState extends StepState {
  progress?: StepProgress;
}

export type CreateStepsState = Record<CreateStepId, CreateStepState>;

/** Steps in workflow order; the StepCard titles carry the sequence. */
export const CREATE_STEP_ORDER: readonly CreateStepId[] = [
  "fetch",
  "json",
  "categorize",
  "bgRemoval",
  "imageGen",
  "textGen",
  "createListing",
];

export const CREATE_STEP_TITLES: Record<CreateStepId, string> = {
  fetch: "Step 1 — Fetch listing from eBay",
  json: "Step 2 — Create initial JSON file",
  categorize: "Step 3 — Categorize images",
  bgRemoval: "Step 4 — Remove backgrounds",
  imageGen: "Step 5 — Generate images",
  textGen: "Step 6 — Generate text",
  createListing: "Step 7 — Create listing",
};

/**
 * Maps the step names the /api/photos NDJSON stream emits to Create step ids.
 * All three stream steps belong to the fetch phase (one HTTP request).
 */
export const FETCH_STREAM_STEP_IDS: Record<string, CreateStepId> = {
  "Fetching listing from eBay": "fetch",
  "Creating initial JSON file": "json",
  "Categorizing images": "categorize",
};

const FETCH_PHASE_STEPS: readonly CreateStepId[] = ["fetch", "json", "categorize"];

/** Which optional steps the user's settings skip for a run. */
export interface CreateStepSettings {
  classify: boolean;
  bgRemoval: boolean;
}

export function skippedCreateStepIds(settings: CreateStepSettings): CreateStepId[] {
  const skipped: CreateStepId[] = [];
  if (!settings.classify) skipped.push("categorize");
  if (!settings.bgRemoval) skipped.push("bgRemoval");
  return skipped;
}

export function initialCreateSteps(): CreateStepsState {
  return {
    fetch: { status: "pending" },
    json: { status: "pending" },
    categorize: { status: "pending" },
    bgRemoval: { status: "pending" },
    imageGen: { status: "pending" },
    textGen: { status: "pending" },
    createListing: { status: "pending" },
  };
}

/** Merge a patch into one step, leaving the rest untouched. */
export function patchCreateStep(
  steps: CreateStepsState,
  id: CreateStepId,
  patch: Partial<CreateStepState>,
): CreateStepsState {
  return { ...steps, [id]: { ...steps[id], ...patch } };
}

/** Mark a step running; clears any prior error/progress (e.g. on retry). */
export function startCreateStep(
  steps: CreateStepsState,
  id: CreateStepId,
  statusText?: string,
): CreateStepsState {
  return patchCreateStep(steps, id, {
    status: "running",
    statusText,
    error: undefined,
    progress: undefined,
  });
}

export function succeedCreateStep(
  steps: CreateStepsState,
  id: CreateStepId,
  statusText?: string,
): CreateStepsState {
  return patchCreateStep(steps, id, { status: "success", statusText, error: undefined });
}

/**
 * Complete every step up to and including `throughId` — the local-state
 * equivalent of the old pipeline's advancePast, for steps that finish out of
 * order (e.g. text generation completes while images still generate).
 * Optional steps skipped by settings stay pending; they render disabled.
 */
export function succeedCreateStepsThrough(
  steps: CreateStepsState,
  throughId: CreateStepId,
  settings: CreateStepSettings,
): CreateStepsState {
  const skipped = new Set(skippedCreateStepIds(settings));
  const throughIndex = CREATE_STEP_ORDER.indexOf(throughId);
  const next = { ...steps };
  for (const id of CREATE_STEP_ORDER) {
    if (CREATE_STEP_ORDER.indexOf(id) > throughIndex) break;
    if (skipped.has(id)) continue;
    next[id] = { ...next[id], status: "success", error: undefined };
  }
  return next;
}

/**
 * Fail a step of a phase with an inline error. Fails the phase's running
 * step; when none is running (e.g. the stream died between steps), fails the
 * first step that never completed.
 */
export function failCreatePhaseStep(
  steps: CreateStepsState,
  phaseIds: readonly CreateStepId[],
  error: string,
): CreateStepsState {
  const target =
    phaseIds.find((id) => steps[id].status === "running") ??
    phaseIds.find((id) => steps[id].status !== "success");
  if (!target) return steps;
  return patchCreateStep(steps, target, { status: "error", error });
}

/** The fetch phase is steps 1–3; exported for the fetch error path. */
export const CREATE_FETCH_PHASE_STEPS = FETCH_PHASE_STEPS;

/**
 * Phase-based retry (was createFailedPhaseRef): which phase a failed step's
 * Retry re-runs. Retrying "images" re-confirms the categories (image
 * generation re-runs); retrying "textGen" re-runs text generation; retrying
 * "create" re-runs only create-listing.
 */
export type CreateRetryPhase = "fetch" | "images" | "textGen" | "create";

export function createRetryPhaseForStep(id: CreateStepId): CreateRetryPhase {
  if (id === "createListing") return "create";
  if (id === "textGen") return "textGen";
  if (FETCH_PHASE_STEPS.includes(id)) return "fetch";
  return "images";
}
