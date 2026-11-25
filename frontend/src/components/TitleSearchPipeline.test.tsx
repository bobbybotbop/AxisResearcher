// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import TitleSearchPipeline from "./TitleSearchPipeline";
import { toast } from "../utils/toasts";

(globalThis as Record<string, unknown>).IS_REACT_ACT_ENVIRONMENT = true;

// --- helpers ---------------------------------------------------------------

const jsonResponse = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

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

/** A stream that delivers progress events but never closes (step still running). */
const hangingNdjsonResponse = (events: unknown[]) => {
  const text = events.map((e) => JSON.stringify(e)).join("\n") + "\n";
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode(text));
      },
    }),
    { status: 200 },
  );
};

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

const WHITELISTED_RESULT = {
  title: "Test Widget 3D file",
  link: "https://www.thingiverse.com/thing:123",
  snippet: "",
  site_type: "whitelisted",
  priority_rank: 1,
};

const happyPathHandlers = (): Record<string, FetchHandler> => ({
  "/api/photos/": () =>
    ndjsonResponse([
      { type: "progress", step: "Fetching listing", status: "in_progress" },
      { type: "progress", step: "Downloading photos", status: "in_progress" },
      {
        type: "result",
        data: { photos: ["p1", "p2"], listing: { title: "Test Widget" } },
      },
    ]),
  "/api/optimize-title": () => jsonResponse({ optimized_title: "Test Widget Optimized" }),
  "/api/serp-text-search": () => jsonResponse({ results: [WHITELISTED_RESULT] }),
  "/api/scrape-site-images": () => jsonResponse({ images: ["s1", "s2"] }),
  "/api/compare-images": () => jsonResponse({ match: true }),
});

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
    root.render(createElement(TitleSearchPipeline));
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

const STEP1 = "Step 1 — Fetch eBay Listing";
const STEP2 = "Step 2 — Optimize Title & Search";
const STEP3 = "Step 3 — Confirm Match";

// --- tests -----------------------------------------------------------------

describe("TitleSearchPipeline", () => {
  it("renders all three steps as cards; steps 2 and 3 are disabled until their dependencies are met", () => {
    const step1 = cardFor(STEP1);
    const step2 = cardFor(STEP2);
    const step3 = cardFor(STEP3);
    expect(step1.getAttribute("aria-disabled")).toBeNull();
    expect(step2.getAttribute("aria-disabled")).toBe("true");
    expect(step3.getAttribute("aria-disabled")).toBe("true");
    // All pending: no spinner, no success check, no error icon
    expect(container.querySelector(".animate-spin")).toBeNull();
    expect(container.textContent).not.toContain("✓");
    expect(container.textContent).not.toContain("✕");
  });

  it("step 1 status line follows the NDJSON stream messages while running", async () => {
    installFetchMock({
      "/api/photos/": () =>
        hangingNdjsonResponse([
          { type: "progress", step: "Fetching listing", status: "in_progress" },
          { type: "progress", step: "Downloading photos", status: "in_progress" },
        ]),
    });
    const input = container.querySelector<HTMLInputElement>('input[aria-label="eBay listing URL"]')!;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
    act(() => {
      setter.call(input, "https://www.ebay.com/itm/123");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    act(() => {
      input.closest("form")!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await drain(10);
    const step1 = cardFor(STEP1);
    expect(statusLineOf(step1)).toBe("Downloading photos…");
    expect(step1.querySelector(".animate-spin")).not.toBeNull();
  });

  it("happy path: fetch → optimize → search → confirm, each step reports success in its own card", async () => {
    installFetchMock(happyPathHandlers());
    await submitListing("https://www.ebay.com/itm/123");

    const step1 = cardFor(STEP1);
    expect(statusLineOf(step1)).toBe("2 photos found");
    expect(step1.textContent).toContain("✓");

    const step2 = cardFor(STEP2);
    expect(step2.getAttribute("aria-disabled")).toBeNull();
    expect(statusLineOf(step2)).toBe("1 whitelisted result found");
    expect(step2.textContent).toContain("Test Widget Optimized");

    const step3 = cardFor(STEP3);
    expect(step3.getAttribute("aria-disabled")).toBeNull();
    expect(statusLineOf(step3)).toBe("Confirmed image match");
    expect(step3.textContent).toContain("✓");
    expect(step3.textContent).toContain("Use this link →");
  });

  it("step 1 failure: inline error + Retry at step 1 and an error toast; Retry re-fetches", async () => {
    const errorSpy = vi.spyOn(toast, "error");
    const calls = installFetchMock({
      "/api/photos/": () => ndjsonResponse([{ type: "error", error: "Listing not found" }]),
    });
    await submitListing("https://www.ebay.com/itm/123");

    const step1 = cardFor(STEP1);
    expect(step1.querySelector('[role="alert"]')?.textContent).toContain("Listing not found");
    expect(errorSpy).toHaveBeenCalledWith("Listing not found");
    // Downstream steps stay pending and disabled
    expect(cardFor(STEP2).getAttribute("aria-disabled")).toBe("true");

    // Retry from the failed step, now succeeding
    installFetchMock(happyPathHandlers());
    const retry = retryButtonOf(step1);
    expect(retry).toBeDefined();
    await click(retry!);
    expect(calls.filter((u) => u.startsWith("/api/photos/"))).toHaveLength(1); // first mock
    expect(statusLineOf(cardFor(STEP1))).toBe("2 photos found");
  });

  it("step 2 failure: inline error + Retry at step 2 and an error toast; Retry re-runs the search only", async () => {
    const errorSpy = vi.spyOn(toast, "error");
    let searchCalls = 0;
    const calls = installFetchMock({
      ...happyPathHandlers(),
      "/api/serp-text-search": () => {
        searchCalls += 1;
        return jsonResponse({ error: "SerpAPI unavailable" }, 500);
      },
    });
    await submitListing("https://www.ebay.com/itm/123");

    const step2 = cardFor(STEP2);
    expect(step2.querySelector('[role="alert"]')?.textContent).toContain("SerpAPI unavailable");
    expect(errorSpy).toHaveBeenCalledWith("SerpAPI unavailable");
    // Step 1 stays successful; step 3 never started
    expect(cardFor(STEP1).textContent).toContain("✓");
    expect(cardFor(STEP3).getAttribute("aria-disabled")).toBe("true");

    installFetchMock(happyPathHandlers());
    const retry = retryButtonOf(step2);
    expect(retry).toBeDefined();
    await click(retry!);

    // Retry re-ran the search, not the fetch
    expect(searchCalls).toBe(1);
    expect(calls.filter((u) => u.startsWith("/api/photos/"))).toHaveLength(1);
    expect(statusLineOf(cardFor(STEP2))).toBe("1 whitelisted result found");
    expect(statusLineOf(cardFor(STEP3))).toBe("Confirmed image match");
  });

  it("no results: retries once with a shortened query, then proceeds with the shortened results", async () => {
    let searchCalls = 0;
    let shortenCalls = 0;
    installFetchMock({
      ...happyPathHandlers(),
      "/api/serp-text-search": () => {
        searchCalls += 1;
        return searchCalls === 1
          ? jsonResponse({ results: [] })
          : jsonResponse({ results: [WHITELISTED_RESULT] });
      },
      "/api/shorten-title": () => {
        shortenCalls += 1;
        return jsonResponse({ shortened_title: "Widget" });
      },
    });
    await submitListing("https://www.ebay.com/itm/123");

    expect(shortenCalls).toBe(1);
    expect(searchCalls).toBe(2);
    const step2 = cardFor(STEP2);
    expect(step2.textContent).toContain("retried with:");
    expect(statusLineOf(step2)).toBe("1 whitelisted result found");
  });

  it("no results even after the shortened retry: inline success message, no error toast", async () => {
    const errorSpy = vi.spyOn(toast, "error");
    installFetchMock({
      ...happyPathHandlers(),
      "/api/serp-text-search": () => jsonResponse({ results: [] }),
      "/api/shorten-title": () => jsonResponse({ shortened_title: "Widget" }),
    });
    await submitListing("https://www.ebay.com/itm/123");

    const step2 = cardFor(STEP2);
    expect(statusLineOf(step2)).toBe("No 3D file results found for this title");
    expect(step2.textContent).toContain("✓");
    expect(step2.querySelector('[role="alert"]')).toBeNull();
    expect(errorSpy).not.toHaveBeenCalled();
    // No viable link: step 3 stays disabled
    expect(cardFor(STEP3).getAttribute("aria-disabled")).toBe("true");
  });
});
