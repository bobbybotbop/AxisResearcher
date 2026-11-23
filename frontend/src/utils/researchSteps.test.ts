import { describe, expect, it } from "vitest";
import {
  applyResearchProgressEvent,
  createResearchSteps,
  failRunningResearchStep,
  RESEARCH_STEP_TITLES,
} from "./researchSteps";

describe("createResearchSteps", () => {
  it("returns one pending step per Research Pipeline step title", () => {
    const steps = createResearchSteps();
    expect(steps).toHaveLength(4);
    expect(RESEARCH_STEP_TITLES).toEqual([
      "Step 1 — Checking API budget",
      "Step 2 — Collecting seller listings",
      "Step 3 — Fetching listing details",
      "Step 4 — Computing metrics",
    ]);
    for (const step of steps) {
      expect(step.status).toBe("pending");
      expect(step.statusText).toBeUndefined();
      expect(step.progress).toBeUndefined();
      expect(step.error).toBeUndefined();
    }
  });
});

describe("applyResearchProgressEvent", () => {
  it("budget in_progress starts step 1 with the cost figures in the status line", () => {
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Checking API budget",
      status: "in_progress",
      used_today: 120,
      estimated_cost: 550,
    });
    expect(steps[0].status).toBe("running");
    expect(steps[0].statusText).toBe("~550 calls estimated, 120 used today");
    expect(steps[1].status).toBe("pending");
    expect(steps[2].status).toBe("pending");
    expect(steps[3].status).toBe("pending");
  });

  it("budget completed marks step 1 done", () => {
    let steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Checking API budget",
      status: "in_progress",
      used_today: 120,
      estimated_cost: 550,
    });
    steps = applyResearchProgressEvent(steps, {
      step: "Checking API budget",
      status: "completed",
    });
    expect(steps[0].status).toBe("success");
  });

  it("collect completed reports the listing count and marks earlier steps done", () => {
    // Stream jumps straight to collect completing (earlier events missed):
    // advancePast semantics mark everything up to it done.
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Collecting seller listings",
      status: "completed",
      total_listings: 42,
    });
    expect(steps[0].status).toBe("success");
    expect(steps[1].status).toBe("success");
    expect(steps[1].statusText).toBe("42 listings found");
    expect(steps[2].status).toBe("pending");
  });

  it("collect completed singularizes one listing", () => {
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Collecting seller listings",
      status: "completed",
      total_listings: 1,
    });
    expect(steps[1].statusText).toBe("1 listing found");
  });

  it("details completed reports the fetched count", () => {
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Fetching listing details",
      status: "completed",
      fetched: 38,
    });
    expect(steps[0].status).toBe("success");
    expect(steps[1].status).toBe("success");
    expect(steps[2].status).toBe("success");
    expect(steps[2].statusText).toBe("38 listing details fetched");
    expect(steps[3].status).toBe("pending");
  });

  it("metrics in_progress feeds the header count and the listing title", () => {
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Computing metrics (3/10)",
      status: "in_progress",
      title: "Vintage Star Wars Print",
      search_phrase: "star wars print",
    });
    expect(steps[0].status).toBe("success");
    expect(steps[3].status).toBe("running");
    expect(steps[3].progress).toEqual({ current: 3, total: 10 });
    expect(steps[3].statusText).toBe("Computing metrics — Vintage Star Wars Print");
  });

  it("metrics in_progress without a title falls back to a generic line", () => {
    const steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Computing metrics (1/5)",
      status: "in_progress",
    });
    expect(steps[3].status).toBe("running");
    expect(steps[3].progress).toEqual({ current: 1, total: 5 });
    expect(steps[3].statusText).toBe("Computing metrics…");
  });

  it("metrics completed mid-run keeps the step running with updated counts", () => {
    let steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Computing metrics (3/10)",
      status: "in_progress",
      title: "Vintage Star Wars Print",
    });
    steps = applyResearchProgressEvent(steps, {
      step: "Computing metrics (3/10)",
      status: "completed",
    });
    expect(steps[3].status).toBe("running");
    expect(steps[3].progress).toEqual({ current: 3, total: 10 });
  });

  it("metrics completed at N/N finishes the step and clears the count", () => {
    let steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Computing metrics (9/10)",
      status: "in_progress",
      title: "Some Listing",
    });
    steps = applyResearchProgressEvent(steps, {
      step: "Computing metrics (10/10)",
      status: "completed",
    });
    expect(steps[3].status).toBe("success");
    expect(steps[3].statusText).toBe("Metrics computed for 10 listings");
    expect(steps[3].progress).toBeUndefined();
  });

  it("ignores events with an unknown step name or missing fields", () => {
    const initial = createResearchSteps();
    expect(applyResearchProgressEvent(initial, { step: "Something else", status: "completed" })).toBe(initial);
    expect(applyResearchProgressEvent(initial, { status: "in_progress" })).toBe(initial);
    expect(applyResearchProgressEvent(initial, {})).toBe(initial);
  });
});

describe("failRunningResearchStep", () => {
  it("marks the currently running step as the failure", () => {
    let steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Computing metrics (2/10)",
      status: "in_progress",
      title: "Some Listing",
    });
    steps = failRunningResearchStep(steps, "eBay API rate limited");
    expect(steps[0].status).toBe("success");
    expect(steps[3].status).toBe("error");
    expect(steps[3].error).toBe("eBay API rate limited");
    expect(steps[3].progress).toBeUndefined();
    expect(steps[1].status).not.toBe("error");
    expect(steps[2].status).not.toBe("error");
  });

  it("budget-exceeded failure lands on step 1", () => {
    let steps = applyResearchProgressEvent(createResearchSteps(), {
      step: "Checking API budget",
      status: "in_progress",
      used_today: 900,
      estimated_cost: 550,
    });
    steps = failRunningResearchStep(steps, "Daily eBay API budget would be exceeded");
    expect(steps[0].status).toBe("error");
    expect(steps[0].error).toBe("Daily eBay API budget would be exceeded");
    expect(steps[1].status).toBe("pending");
  });

  it("with no running step, fails the first pending step", () => {
    const steps = failRunningResearchStep(createResearchSteps(), "network down");
    expect(steps[0].status).toBe("error");
    expect(steps[0].error).toBe("network down");
    expect(steps[1].status).toBe("pending");
  });

  it("is a no-op when every step already succeeded", () => {
    let steps = createResearchSteps().map(() => ({ status: "success" as const }));
    const before = steps;
    steps = failRunningResearchStep(steps, "late failure");
    expect(steps).toBe(before);
  });
});
