import type { Pipeline } from "./statusStore";

/**
 * Step names for the Create workflow Pipeline (ADR 0002). The whole Create
 * flow — fetch photos → categorize → bg removal → image generation → text
 * generation → create listing — runs as one Pipeline of Tasks reporting to
 * the Status Store. Conditional steps (categorize, bg removal) are included
 * only when their feature is enabled.
 */
export const CREATE_STEP_FETCH = "Fetching listing from eBay";
export const CREATE_STEP_JSON = "Creating initial JSON file";
export const CREATE_STEP_CATEGORIZE = "Categorizing images";
export const CREATE_STEP_BG_REMOVAL = "Removing backgrounds";
export const CREATE_STEP_IMAGE_GEN = "Generating images";
export const CREATE_STEP_TEXT_GEN = "Generating text";
export const CREATE_STEP_CREATE_LISTING = "Creating listing";

export function createPipelineSteps(options: {
  classify: boolean;
  bgRemoval: boolean;
}): string[] {
  const steps = [CREATE_STEP_FETCH, CREATE_STEP_JSON];
  if (options.classify) steps.push(CREATE_STEP_CATEGORIZE);
  if (options.bgRemoval) steps.push(CREATE_STEP_BG_REMOVAL);
  steps.push(CREATE_STEP_IMAGE_GEN, CREATE_STEP_TEXT_GEN, CREATE_STEP_CREATE_LISTING);
  return steps;
}

/** Step names for the Upload-to-eBay Pipeline. */
export const UPLOAD_STEP_PREPARE = "Preparing listing data";
export const UPLOAD_STEP_UPLOAD = "Uploading to eBay";
export const UPLOAD_PIPELINE_STEPS = [UPLOAD_STEP_PREPARE, UPLOAD_STEP_UPLOAD];

export interface CreatePhase {
  /** True while the fetch-photos phase (any fetch step) is running. */
  fetching: boolean;
  /** True while the image-generation step is running (was `isConfirming`). */
  generatingImages: boolean;
  /** True while the create-listing step is running (was `isCreatingListing`). */
  creatingListing: boolean;
  /** Name of the step that failed, when the pipeline is in error state. */
  failedStep: string | null;
  /** True once the pipeline has run past the fetch phase (photos loaded). */
  fetchDone: boolean;
}

const FETCH_STEPS = new Set([CREATE_STEP_FETCH, CREATE_STEP_JSON, CREATE_STEP_CATEGORIZE]);

/**
 * Derive the Create workflow's waiting-state booleans from its Pipeline in
 * the Status Store. Replaces the fetchProgress / imageGenProgress /
 * createListingProgress objects and the isConfirming / isCreatingListing
 * booleans.
 */
export function deriveCreatePhase(pipeline: Pipeline | undefined): CreatePhase {
  if (!pipeline) {
    return {
      fetching: false,
      generatingImages: false,
      creatingListing: false,
      failedStep: null,
      fetchDone: false,
    };
  }
  const current = pipeline.steps[pipeline.currentIndex];
  const running = pipeline.status === "running";
  const firstNonFetchIndex = pipeline.steps.findIndex((s) => !FETCH_STEPS.has(s.name));
  return {
    fetching: running && !!current && FETCH_STEPS.has(current.name),
    generatingImages: running && current?.name === CREATE_STEP_IMAGE_GEN,
    creatingListing: running && current?.name === CREATE_STEP_CREATE_LISTING,
    failedStep:
      pipeline.status === "error"
        ? (pipeline.steps.find((s) => s.status === "error")?.name ?? null)
        : null,
    fetchDone:
      firstNonFetchIndex >= 0 && pipeline.currentIndex >= firstNonFetchIndex,
  };
}
