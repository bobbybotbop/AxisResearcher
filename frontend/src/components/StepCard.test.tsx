import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import StepCard from "./StepCard";

const render = (props: React.ComponentProps<typeof StepCard>) =>
  renderToStaticMarkup(createElement(StepCard, props));

describe("StepCard", () => {
  it("pending: dimmed state icon, no spinner", () => {
    const html = render({ title: "Step 1 — Fetch", status: "pending" });
    expect(html).toContain("Step 1 — Fetch");
    expect(html).not.toContain("animate-spin");
    expect(html).not.toContain("✓");
    expect(html).not.toContain("✕");
  });

  it("running: spinner in the header", () => {
    const html = render({ title: "Step 1", status: "running" });
    expect(html).toContain("animate-spin");
  });

  it("success: persistent subtle green check", () => {
    const html = render({ title: "Step 1", status: "success" });
    expect(html).toContain("✓");
    expect(html).toContain("text-success");
  });

  it("error: red icon, inline error message and Retry button", () => {
    const html = render({
      title: "Step 1",
      status: "error",
      error: "Listing not found",
      onRetry: () => {},
    });
    expect(html).toContain("✕");
    expect(html).toContain("Listing not found");
    expect(html).toContain("Retry");
  });

  it("error without onRetry renders no Retry button", () => {
    const html = render({ title: "Step 1", status: "error", error: "boom" });
    expect(html).toContain("boom");
    expect(html).not.toContain("Retry");
  });

  it("renders determinate progress as 'N of M' in the header", () => {
    const html = render({
      title: "Step 2",
      status: "running",
      progress: { current: 3, total: 8 },
    });
    expect(html).toContain("3 of 8");
  });

  it("renders the single-line status text", () => {
    const html = render({
      title: "Step 1",
      status: "running",
      statusText: "Comparing image 2 of 5…",
    });
    expect(html).toContain("Comparing image 2 of 5…");
    expect(html).toContain("truncate");
  });

  it("disabled: greys out the card and marks it aria-disabled", () => {
    const html = render({ title: "Step 2", status: "pending", disabled: true });
    expect(html).toContain('aria-disabled="true"');
    expect(html).toContain("opacity-");
  });

  it("renders children as the card body", () => {
    const html = render({
      title: "Step 1",
      status: "pending",
      children: createElement("form", null, "body-content"),
    });
    expect(html).toContain("body-content");
  });
});
