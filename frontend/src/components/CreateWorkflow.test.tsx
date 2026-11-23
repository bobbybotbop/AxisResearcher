// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import CreateWorkflow from "./CreateWorkflow";
import {
  CREATE_STEP_TITLES,
  initialCreateSteps,
  patchCreateStep,
  type CreateStepId,
  type CreateStepsState,
} from "../utils/createPipeline";

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

interface RenderOptions {
  createSteps?: CreateStepsState;
  onRetryCreateStep?: (id: CreateStepId) => void;
  listingLinkSubmitted?: boolean;
  loading?: boolean;
  classifyImagesEnabled?: boolean;
  autoBackgroundRemovalEnabled?: boolean;
  isGeneratingText?: boolean;
  textGenStatus?: string;
  listing?: { title?: string };
  editableTitle?: string;
}

function renderWorkflow(options: RenderOptions = {}) {
  act(() => {
    root.render(
      createElement(CreateWorkflow, {
        listingId: "",
        onListingIdChange: () => {},
        onSubmit: (e: React.FormEvent) => e.preventDefault(),
        onChatSubmit: () => {},
        onDragEnd: () => {},
        ...options,
      }),
    );
  });
  return container;
}

describe("CreateWorkflow step cards", () => {
  it("renders every Create step as a StepCard once the workflow is active", () => {
    renderWorkflow({ listingLinkSubmitted: true, createSteps: initialCreateSteps() });
    for (const title of Object.values(CREATE_STEP_TITLES)) {
      expect(container.textContent).toContain(title);
    }
  });

  it("renders no step cards before the workflow starts", () => {
    renderWorkflow({ createSteps: initialCreateSteps() });
    expect(container.textContent).not.toContain(CREATE_STEP_TITLES.fetch);
    expect(container.textContent).not.toContain(CREATE_STEP_TITLES.createListing);
  });

  it("shows determinate progress ('3 of 8') in the image-generation card header", () => {
    const steps = patchCreateStep(initialCreateSteps(), "imageGen", {
      status: "running",
      progress: { current: 3, total: 8 },
    });
    renderWorkflow({ listingLinkSubmitted: true, createSteps: steps });
    expect(container.textContent).toContain("3 of 8");
  });

  it("renders skipped optional steps disabled when their settings are off", () => {
    renderWorkflow({
      listingLinkSubmitted: true,
      createSteps: initialCreateSteps(),
      classifyImagesEnabled: false,
      autoBackgroundRemovalEnabled: false,
    });
    const cards = Array.from(container.querySelectorAll("[aria-disabled='true']"));
    const disabledText = cards.map((c) => c.textContent).join("\n");
    expect(disabledText).toContain(CREATE_STEP_TITLES.categorize);
    expect(disabledText).toContain(CREATE_STEP_TITLES.bgRemoval);
  });

  it("a failed step shows its error inline with a Retry button that re-runs that step", () => {
    const onRetryCreateStep = vi.fn();
    const steps = patchCreateStep(initialCreateSteps(), "imageGen", {
      status: "error",
      error: "Image generation failed",
    });
    renderWorkflow({
      listingLinkSubmitted: true,
      createSteps: steps,
      onRetryCreateStep,
    });
    expect(container.textContent).toContain("Image generation failed");
    const retryButtons = Array.from(container.querySelectorAll("button")).filter(
      (b) => b.textContent === "Retry",
    );
    expect(retryButtons).toHaveLength(1);
    act(() => retryButtons[0].click());
    expect(onRetryCreateStep).toHaveBeenCalledWith("imageGen");
  });

  it("narrates text generation in the step's status line while streaming", () => {
    const steps = patchCreateStep(initialCreateSteps(), "textGen", {
      status: "running",
      statusText: "AI is writing…",
    });
    renderWorkflow({
      listingLinkSubmitted: true,
      createSteps: steps,
      listing: { title: "Some listing" },
      editableTitle: "",
      isGeneratingText: true,
      textGenStatus: "writing",
    });
    expect(container.textContent).toContain("AI is writing…");
  });

  it("renders no create-workflow PipelineTracker (steps own their status)", () => {
    renderWorkflow({ listingLinkSubmitted: true, createSteps: initialCreateSteps() });
    // The old tracker rendered step names as plain rows; the cards render the
    // numbered titles. A tracker would duplicate the step list.
    const matches = container.textContent!.match(/Step 1 — Fetch listing from eBay/g);
    expect(matches).toHaveLength(1);
  });
});
