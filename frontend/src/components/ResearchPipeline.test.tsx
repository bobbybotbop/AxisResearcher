import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ResearchPipeline from "./ResearchPipeline";
import { RESEARCH_STEP_TITLES } from "../utils/researchSteps";

// Initial render (no run started): the four Research Pipeline steps render as
// pending StepCards, each owning its status display (ADR 0003).
describe("ResearchPipeline", () => {
  it("renders the four pipeline steps as cards before any run", () => {
    const html = renderToStaticMarkup(createElement(ResearchPipeline));
    for (const title of RESEARCH_STEP_TITLES) {
      expect(html).toContain(title);
    }
    // All four pending: no spinner, no success check, no error mark.
    expect(html).not.toContain("animate-spin");
    expect(html).not.toContain("✓");
    expect(html).not.toContain("✕");
    expect(html).toContain("Run Copy Seller");
  });
});
