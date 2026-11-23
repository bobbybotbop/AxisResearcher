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

  it("Step 4 is disabled until Step 3 has produced a file; Step 3 stays enabled", () => {
    const html = render();
    // Exactly one disabled card, and it is the one whose header reads Step 4
    // (the disabled card's opening tag lands just before its title).
    const disabledAt = html.indexOf('aria-disabled="true"');
    expect(disabledAt).toBeGreaterThan(-1);
    expect(disabledAt).toBe(html.lastIndexOf('aria-disabled="true"'));
    const step4TitleAt = html.indexOf("Step 4 — Studio Render");
    expect(disabledAt).toBeLessThan(step4TitleAt);
    expect(step4TitleAt - disabledAt).toBeLessThan(300);
    expect(html.indexOf("Step 3 — Download 3D File")).toBeLessThan(disabledAt);
  });

  it("starts with no inline error or Retry button", () => {
    const html = render();
    expect(html).not.toContain('role="alert"');
    expect(html).not.toContain("Retry");
  });
});
