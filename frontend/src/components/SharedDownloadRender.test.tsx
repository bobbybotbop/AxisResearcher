import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import SharedDownloadRender from "./SharedDownloadRender";

// StepCard's dimmed pending state icon (see StepCard.tsx)
const PENDING_ICON = "border-text-muted/30";

const render = () => renderToStaticMarkup(createElement(SharedDownloadRender, {}));

describe("SharedDownloadRender", () => {
  it("renders Download (Step 3) and Studio Render (Step 4) as pending StepCards", () => {
    const html = render();
    expect(html).toContain("Step 3 — Download 3D File");
    expect(html).toContain("Step 4 — Studio Render");
    // Each step owns its waiting-state display (ADR 0003): two dimmed pending
    // icons, one per StepCard. The old PipelineTracker rendered nothing here.
    expect(html.split(PENDING_ICON).length - 1).toBe(2);
  });

  it("starts with no inline error or Retry button", () => {
    const html = render();
    expect(html).not.toContain('role="alert"');
    expect(html).not.toContain("Retry");
  });
});
