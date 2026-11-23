import type { StepStatus } from "../components/StepCard";

/**
 * Upload-to-eBay step state (ADR 0003). The Upload flow — prepare listing
 * data → upload to eBay — runs inside a single /api/upload-listing NDJSON
 * stream; these pure helpers are the state machine the workflow component
 * drives from local useState. No Status Store, no PipelineTracker.
 */

export type UploadStepId = "prepare" | "upload";

export interface UploadStepState {
  status: StepStatus;
  statusText?: string;
  error?: string;
}

export type UploadStepsState = Record<UploadStepId, UploadStepState>;

/** Steps in workflow order; the StepCard titles carry the sequence. */
export const UPLOAD_STEP_ORDER: readonly UploadStepId[] = ["prepare", "upload"];

export const UPLOAD_STEP_TITLES: Record<UploadStepId, string> = {
  prepare: "Prepare listing data",
  upload: "Upload to eBay",
};

/**
 * Maps the step names the /api/upload-listing NDJSON stream emits to Upload
 * step ids. Both stream steps belong to the one HTTP request.
 */
const UPLOAD_STREAM_STEP_IDS: Record<string, UploadStepId> = {
  "Preparing listing data": "prepare",
  "Uploading to eBay": "upload",
};

function initialUploadSteps(): UploadStepsState {
  return {
    prepare: { status: "pending" },
    upload: { status: "pending" },
  };
}

function patchUploadStep(
  steps: UploadStepsState,
  id: UploadStepId,
  patch: Partial<UploadStepState>,
): UploadStepsState {
  return { ...steps, [id]: { ...steps[id], ...patch } };
}

/**
 * Begin a run (or retry): the prepare step starts running, everything else
 * resets — a failed run's error is cleared so the retry starts clean.
 */
export function startUploadRun(): UploadStepsState {
  return patchUploadStep(initialUploadSteps(), "prepare", {
    status: "running",
    statusText: "Preparing listing data…",
  });
}

/** The progress event shape the /api/upload-listing NDJSON stream emits. */
export interface UploadStreamEvent {
  step?: string;
  status?: string;
}

/**
 * Apply one stream event: in_progress marks the step running with a status
 * line; completed marks every step up to and including it success and the
 * next step running. Unknown step names are ignored.
 */
export function applyUploadStreamEvent(
  steps: UploadStepsState,
  event: UploadStreamEvent,
): UploadStepsState {
  const id = event.step ? UPLOAD_STREAM_STEP_IDS[event.step] : undefined;
  if (!id) return steps;
  if (event.status === "in_progress") {
    return patchUploadStep(steps, id, {
      status: "running",
      statusText: `${event.step}…`,
      error: undefined,
    });
  }
  if (event.status === "completed") {
    const targetIndex = UPLOAD_STEP_ORDER.indexOf(id);
    const next = { ...steps };
    UPLOAD_STEP_ORDER.forEach((stepId, i) => {
      if (i <= targetIndex) {
        next[stepId] = { ...next[stepId], status: "success", error: undefined };
      } else if (i === targetIndex + 1) {
        next[stepId] = {
          ...next[stepId],
          status: "running",
          statusText: next[stepId].statusText,
          error: undefined,
        };
      }
    });
    return next;
  }
  return steps;
}

/** Mark the whole run success; the status line lands on the final step. */
export function succeedUploadRun(
  steps: UploadStepsState,
  statusText?: string,
): UploadStepsState {
  return {
    prepare: { ...steps.prepare, status: "success", error: undefined },
    upload: { ...steps.upload, status: "success", statusText, error: undefined },
  };
}

/**
 * Fail a step with an inline error. Fails the running step; when none is
 * running (e.g. the stream died between steps), fails the first step that
 * never completed. A fully successful run is left untouched.
 */
export function failUploadStep(steps: UploadStepsState, error: string): UploadStepsState {
  const target =
    UPLOAD_STEP_ORDER.find((id) => steps[id].status === "running") ??
    UPLOAD_STEP_ORDER.find((id) => steps[id].status !== "success");
  if (!target) return steps;
  return patchUploadStep(steps, target, { status: "error", error });
}
