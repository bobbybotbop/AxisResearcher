import { describe, expect, it } from "vitest";
import {
  CREATE_STEP_ORDER,
  FETCH_STREAM_STEP_IDS,
  createRetryPhaseForStep,
  failCreatePhaseStep,
  initialCreateSteps,
  patchCreateStep,
  startCreateStep,
  succeedCreateStep,
  succeedCreateStepsThrough,
} from "./createPipeline";

const NO_SKIP = { classify: true, bgRemoval: true };

describe("initialCreateSteps", () => {
  it("starts every step pending with no error/progress", () => {
    const steps = initialCreateSteps();
    expect(CREATE_STEP_ORDER).toEqual([
      "fetch",
      "json",
      "categorize",
      "bgRemoval",
      "imageGen",
      "textGen",
      "createListing",
    ]);
    for (const id of CREATE_STEP_ORDER) {
      expect(steps[id]).toEqual({ status: "pending" });
    }
  });
});

describe("startCreateStep", () => {
  it("marks the step running with a status line and clears prior error/progress", () => {
    const failed = failCreatePhaseStep(
      startCreateStep(initialCreateSteps(), "imageGen", "Generating images…"),
      ["imageGen"],
      "boom",
    );
    const retried = startCreateStep(failed, "imageGen", "Generating images…");
    expect(retried.imageGen).toEqual({
      status: "running",
      statusText: "Generating images…",
    });
  });

  it("does not touch other steps", () => {
    const steps = startCreateStep(initialCreateSteps(), "fetch", "Fetching…");
    expect(steps.json.status).toBe("pending");
  });
});

describe("succeedCreateStep", () => {
  it("marks the step success with an optional status line", () => {
    const steps = succeedCreateStep(
      startCreateStep(initialCreateSteps(), "fetch"),
      "fetch",
      "8 photos found",
    );
    expect(steps.fetch).toEqual({ status: "success", statusText: "8 photos found" });
  });
});

describe("patchCreateStep", () => {
  it("merges a patch into one step", () => {
    const steps = patchCreateStep(
      startCreateStep(initialCreateSteps(), "imageGen"),
      "imageGen",
      { progress: { current: 3, total: 8 } },
    );
    expect(steps.imageGen.progress).toEqual({ current: 3, total: 8 });
    expect(steps.imageGen.status).toBe("running");
  });
});

describe("succeedCreateStepsThrough", () => {
  it("completes every step up to and including the target, leaving later steps pending", () => {
    const steps = succeedCreateStepsThrough(
      startCreateStep(initialCreateSteps(), "fetch"),
      "categorize",
      NO_SKIP,
    );
    expect(steps.fetch.status).toBe("success");
    expect(steps.json.status).toBe("success");
    expect(steps.categorize.status).toBe("success");
    expect(steps.bgRemoval.status).toBe("pending");
    expect(steps.imageGen.status).toBe("pending");
  });

  it("leaves skipped optional steps pending (they render disabled, never run)", () => {
    const steps = succeedCreateStepsThrough(
      initialCreateSteps(),
      "bgRemoval",
      { classify: false, bgRemoval: false },
    );
    expect(steps.fetch.status).toBe("success");
    expect(steps.json.status).toBe("success");
    expect(steps.categorize.status).toBe("pending");
    expect(steps.bgRemoval.status).toBe("pending");
    expect(steps.imageGen.status).toBe("pending");
  });

  it("marks an already-complete earlier step success without erroring", () => {
    const steps = succeedCreateStepsThrough(
      succeedCreateStepsThrough(initialCreateSteps(), "json", NO_SKIP),
      "textGen",
      NO_SKIP,
    );
    expect(steps.textGen.status).toBe("success");
    expect(steps.createListing.status).toBe("pending");
  });
});

describe("failCreatePhaseStep", () => {
  it("fails the currently running step of the phase with the error message", () => {
    const steps = failCreatePhaseStep(
      succeedCreateStepsThrough(
        startCreateStep(initialCreateSteps(), "json"),
        "fetch",
        NO_SKIP,
      ),
      ["fetch", "json", "categorize"],
      "eBay is down",
    );
    expect(steps.json.status).toBe("error");
    expect(steps.json.error).toBe("eBay is down");
    expect(steps.fetch.status).toBe("success");
    expect(steps.categorize.status).toBe("pending");
  });

  it("falls back to the first non-success step when none is running", () => {
    const steps = failCreatePhaseStep(
      succeedCreateStepsThrough(initialCreateSteps(), "fetch", NO_SKIP),
      ["fetch", "json", "categorize"],
      "boom",
    );
    expect(steps.json.status).toBe("error");
  });
});

describe("FETCH_STREAM_STEP_IDS", () => {
  it("maps the backend /api/photos stream step names to step ids", () => {
    expect(FETCH_STREAM_STEP_IDS["Fetching listing from eBay"]).toBe("fetch");
    expect(FETCH_STREAM_STEP_IDS["Creating initial JSON file"]).toBe("json");
    expect(FETCH_STREAM_STEP_IDS["Categorizing images"]).toBe("categorize");
  });
});

describe("createRetryPhaseForStep", () => {
  it("maps each step to the phase its retry re-runs", () => {
    expect(createRetryPhaseForStep("fetch")).toBe("fetch");
    expect(createRetryPhaseForStep("json")).toBe("fetch");
    expect(createRetryPhaseForStep("categorize")).toBe("fetch");
    expect(createRetryPhaseForStep("bgRemoval")).toBe("images");
    expect(createRetryPhaseForStep("imageGen")).toBe("images");
    expect(createRetryPhaseForStep("textGen")).toBe("textGen");
    expect(createRetryPhaseForStep("createListing")).toBe("create");
  });
});
