// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import ImageSearchSteps from "./ImageSearchSteps";
import { toast } from "../utils/toasts";

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

// --- helpers ---------------------------------------------------------------

const ndjsonResponse = (events: unknown[]) => {
  const text = events.map((e) => JSON.stringify(e)).join("\n") + "\n";
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(text));
        controller.close();
      },
    }),
    { status: 200 },
  );
};

const successPhotosResponse = () =>
  ndjsonResponse([
    { type: "progress", step: "Fetching listing", status: "in_progress" },
    {
      type: "result",
      data: { photos: ["p1", "p2"], listing: { title: "Test Widget" } },
    },
  ]);

type FetchHandler = (url: string) => Response | Promise<Response>;

const installFetchMock = (handlers: Record<string, FetchHandler>) => {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      for (const [prefix, handler] of Object.entries(handlers)) {
        if (url.startsWith(prefix)) return handler(url);
      }
      throw new Error(`unmocked fetch: ${url}`);
    }),
  );
  return calls;
};

// --- DOM plumbing ----------------------------------------------------------

let container: HTMLDivElement;
let root: Root;

const drain = async (rounds = 30) => {
  for (let i = 0; i < rounds; i++) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
  }
};

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(createElement(ImageSearchSteps));
  });
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const cardFor = (title: string): HTMLElement => {
  const p = [...container.querySelectorAll("p")].find((el) => el.textContent === title);
  if (!p) throw new Error(`step card not found: ${title}`);
  // title <p> → header <div> → card <div>
  return p.parentElement!.parentElement as HTMLElement;
};

const statusLineOf = (card: HTMLElement) =>
  card.querySelector('[aria-live="polite"]')?.textContent ?? null;

const retryButtonOf = (card: HTMLElement) =>
  [...card.querySelectorAll("button")].find((b) => b.textContent === "Retry");

const click = async (el: HTMLElement) => {
  act(() => {
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
  await drain();
};

const submitListing = async (url: string) => {
  const input = container.querySelector<HTMLInputElement>('input[aria-label="eBay listing URL"]');
  if (!input) throw new Error("listing input not found");
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(input, url);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const form = input.closest("form")!;
  act(() => {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  await drain();
};

const STEP1 = "Step 1 — Fetch eBay Photos";
const STEP2 = "Step 2 — Reverse Image Search";
const LISTING_URL = "https://www.ebay.com/itm/123";

// --- tests -----------------------------------------------------------------

describe("ImageSearchSteps", () => {
  it("renders both steps as enabled pending cards — step 2 accepts any pasted URL, so it is not gated on step 1", () => {
    expect(cardFor(STEP1).getAttribute("aria-disabled")).toBeNull();
    expect(cardFor(STEP2).getAttribute("aria-disabled")).toBeNull();
    expect(container.querySelector(".animate-spin")).toBeNull();
    expect(container.textContent).not.toContain("✓");
    expect(container.textContent).not.toContain("✕");
  });

  it("step 1 happy path: photos found reported inline in the step 1 card", async () => {
    installFetchMock({ "/api/photos/": successPhotosResponse });
    await submitListing(LISTING_URL);

    const step1 = cardFor(STEP1);
    expect(statusLineOf(step1)).toBe("2 photos found");
    expect(step1.textContent).toContain("✓");
  });

  it("step 1 first-attempt failure: inline error + Retry + error toast; Retry re-fetches the submitted URL after the input cleared", async () => {
    const errorSpy = vi.spyOn(toast, "error");
    installFetchMock({
      "/api/photos/": () => ndjsonResponse([{ type: "error", error: "Listing not found" }]),
    });
    await submitListing(LISTING_URL);

    const step1 = cardFor(STEP1);
    expect(step1.querySelector('[role="alert"]')?.textContent).toContain("Listing not found");
    expect(errorSpy).toHaveBeenCalledWith("Listing not found");
    // The input clears after submit — Retry must still re-run with the submitted URL
    const input = container.querySelector<HTMLInputElement>('input[aria-label="eBay listing URL"]')!;
    expect(input.value).toBe("");
    const retry = retryButtonOf(step1);
    expect(retry).toBeDefined();

    const calls = installFetchMock({ "/api/photos/": successPhotosResponse });
    await click(retry!);

    expect(calls.filter((u) => u.startsWith(`/api/photos/${encodeURIComponent(LISTING_URL)}`))).toHaveLength(1);
    expect(statusLineOf(cardFor(STEP1))).toBe("2 photos found");
    expect(cardFor(STEP1).textContent).toContain("✓");
  });
});
