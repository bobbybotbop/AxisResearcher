import type { StepProgress, StepStatus } from "../components/StepCard";

/**
 * Per-step waiting state for the Research Pipeline (Copy Seller), driven by
 * local state under ADR 0003. The component owns a ResearchStepState[] in
 * useState and feeds backend stream events (backend/copy_seller.py) through
 * applyResearchProgressEvent; this module is the pure transition logic.
 */
export interface ResearchStepState {
  status: StepStatus;
  statusText?: string;
  progress?: StepProgress;
  error?: string;
}

/** Step titles carry the sequence (ADR 0003 — no overall tracker). */
export const RESEARCH_STEP_TITLES: readonly string[] = [
  "Step 1 — Checking API budget",
  "Step 2 — Collecting seller listings",
  "Step 3 — Fetching listing details",
  "Step 4 — Computing metrics",
];

export function createResearchSteps(): ResearchStepState[] {
  return RESEARCH_STEP_TITLES.map(() => ({ status: "pending" }));
}

// Backend stream step names (backend/copy_seller.py).
const STEP_BUDGET = "Checking API budget";
const STEP_COLLECT = "Collecting seller listings";
const STEP_DETAILS = "Fetching listing details";
const STEP_METRICS = "Computing metrics";
const SIMPLE_STEPS = [STEP_BUDGET, STEP_COLLECT, STEP_DETAILS];

/** The subset of a stream progress event this reducer reads. */
export interface ResearchProgressEvent {
  step?: unknown;
  status?: unknown;
  title?: unknown;
  search_phrase?: unknown;
  total_listings?: unknown;
  fetched?: unknown;
  used_today?: unknown;
  estimated_cost?: unknown;
}

function replaceStep(
  steps: ResearchStepState[],
  index: number,
  next: ResearchStepState,
): ResearchStepState[] {
  return steps.map((step, i) => (i === index ? next : step));
}

function budgetStatusText(event: ResearchProgressEvent): string {
  const used = event.used_today;
  const cost = event.estimated_cost;
  if (typeof used === "number" && typeof cost === "number") {
    return `~${cost} calls estimated, ${used} used today`;
  }
  return "Checking API budget…";
}

function completedStatusText(
  stepName: string,
  event: ResearchProgressEvent,
): string {
  if (stepName === STEP_COLLECT && typeof event.total_listings === "number") {
    const n = event.total_listings;
    return `${n} listing${n !== 1 ? "s" : ""} found`;
  }
  if (stepName === STEP_DETAILS && typeof event.fetched === "number") {
    return `${event.fetched} listing details fetched`;
  }
  if (stepName === STEP_BUDGET) return "Budget OK";
  return `${stepName} done`;
}

// Events may arrive after earlier ones were missed (or complete out of
// order); everything before the reporting step is done by definition.
function succeedThrough(
  steps: ResearchStepState[],
  index: number,
): ResearchStepState[] {
  return steps.map((step, i) =>
    i < index && step.status !== "success"
      ? { status: "success", statusText: step.statusText }
      : step,
  );
}

// The metrics step streams one "Computing metrics (i/N)" event per listing;
// the (i/N) count is the step's determinate header progress.
function applyMetricsEvent(
  steps: ResearchStepState[],
  stepName: string,
  status: string,
  event: ResearchProgressEvent,
): ResearchStepState[] {
  const index = SIMPLE_STEPS.length; // metrics is the last step
  const match = stepName.match(/\((\d+)\/(\d+)\)/);
  const counts = match
    ? { current: Number(match[1]), total: Number(match[2]) }
    : null;
  const prior = succeedThrough(steps, index);

  if (status === "in_progress") {
    const title = typeof event.title === "string" && event.title ? event.title : null;
    return replaceStep(prior, index, {
      status: "running",
      statusText: title ? `Computing metrics — ${title}` : "Computing metrics…",
      ...(counts ? { progress: counts } : {}),
    });
  }
  if (status === "completed" && counts) {
    if (counts.current >= counts.total) {
      return replaceStep(prior, index, {
        status: "success",
        statusText: `Metrics computed for ${counts.total} listings`,
      });
    }
    const running = prior[index].status === "running" ? prior[index] : { status: "running" as const };
    return replaceStep(prior, index, { ...running, status: "running", progress: counts });
  }
  return steps;
}

export function applyResearchProgressEvent(
  steps: ResearchStepState[],
  event: ResearchProgressEvent,
): ResearchStepState[] {
  const stepName = typeof event.step === "string" ? event.step : "";
  const status = typeof event.status === "string" ? event.status : "";
  if (!stepName) return steps;
  if (stepName.startsWith(STEP_METRICS)) {
    return applyMetricsEvent(steps, stepName, status, event);
  }

  const index = SIMPLE_STEPS.indexOf(stepName);
  if (index === -1) return steps;

  if (status === "in_progress") {
    return replaceStep(succeedThrough(steps, index), index, {
      status: "running",
      statusText: stepName === STEP_BUDGET ? budgetStatusText(event) : `${stepName}…`,
    });
  }
  if (status === "completed") {
    return replaceStep(succeedThrough(steps, index), index, {
      status: "success",
      statusText: completedStatusText(stepName, event),
    });
  }
  return steps;
}

/**
 * Attribute a thrown run failure to a step: the one currently running (the
 * backend errors out mid-step), or the first pending step if the failure
 * happened before any step reported. No-op when nothing can be blamed.
 */
export function failRunningResearchStep(
  steps: ResearchStepState[],
  error: string,
): ResearchStepState[] {
  let index = steps.findIndex((step) => step.status === "running");
  if (index === -1) index = steps.findIndex((step) => step.status === "pending");
  if (index === -1) return steps;
  return replaceStep(steps, index, { status: "error", error });
}
