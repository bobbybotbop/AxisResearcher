import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { dismissToast, startTaskToast, toast, toastStore } from "./toasts";

const SUCCESS_DISMISS_MS = 5000;

function clearAll(): void {
  for (const t of toastStore.getSnapshot().toasts) dismissToast(t.id);
}

beforeEach(() => {
  vi.useFakeTimers();
  clearAll();
});

afterEach(() => {
  clearAll();
  vi.useRealTimers();
});

describe("toast direct-call API", () => {
  it("error toast renders with the message and persists until dismissed", () => {
    toast.error("Something broke");

    const { toasts } = toastStore.getSnapshot();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].status).toBe("error");
    expect(toasts[0].title).toBe("Something broke");

    vi.advanceTimersByTime(60_000);
    expect(toastStore.getSnapshot().toasts).toHaveLength(1);

    dismissToast(toasts[0].id);
    expect(toastStore.getSnapshot().toasts).toHaveLength(0);
  });

  it("success toast auto-dismisses after ~5s", () => {
    toast.success("Done");
    expect(toastStore.getSnapshot().toasts).toHaveLength(1);
    expect(toastStore.getSnapshot().toasts[0].status).toBe("success");

    vi.advanceTimersByTime(SUCCESS_DISMISS_MS - 1);
    expect(toastStore.getSnapshot().toasts).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(toastStore.getSnapshot().toasts).toHaveLength(0);
  });

  it("info toast behaves like success (auto-dismisses)", () => {
    toast.info("FYI");
    expect(toastStore.getSnapshot().toasts[0].status).toBe("success");
    vi.advanceTimersByTime(SUCCESS_DISMISS_MS);
    expect(toastStore.getSnapshot().toasts).toHaveLength(0);
  });

  it("concurrent toasts stack independently", () => {
    toast.error("first");
    toast.error("second");
    expect(toastStore.getSnapshot().toasts.map((t) => t.title)).toEqual([
      "first",
      "second",
    ]);
  });

  it("notifies subscribers on change", () => {
    const listener = vi.fn();
    const unsubscribe = toastStore.subscribe(listener);
    toast.error("ping");
    expect(listener).toHaveBeenCalled();
    unsubscribe();
  });

  it("never throws on invalid operations", () => {
    expect(() => dismissToast(-1)).not.toThrow();
  });
});

describe("startTaskToast handle API", () => {
  it("shows a pending toast, updates in place, and fails persistently", () => {
    const handle = startTaskToast("Refreshing token");
    expect(toastStore.getSnapshot().toasts[0].status).toBe("pending");

    handle.update("Refreshing token", "contacting eBay");
    const updated = toastStore.getSnapshot().toasts[0];
    expect(updated.title).toBe("Refreshing token");
    expect(updated.message).toBe("contacting eBay");

    handle.fail("token refresh failed");
    const failed = toastStore.getSnapshot().toasts[0];
    expect(failed.status).toBe("error");
    vi.advanceTimersByTime(60_000);
    expect(toastStore.getSnapshot().toasts).toHaveLength(1);
  });

  it("succeed settles the toast and auto-dismisses", () => {
    const handle = startTaskToast("Syncing");
    handle.succeed("synced");
    expect(toastStore.getSnapshot().toasts[0].status).toBe("success");
    expect(toastStore.getSnapshot().toasts[0].message).toBe("synced");
    vi.advanceTimersByTime(SUCCESS_DISMISS_MS);
    expect(toastStore.getSnapshot().toasts).toHaveLength(0);
  });

  it("settled handles ignore further updates", () => {
    const handle = startTaskToast("Task");
    handle.fail("boom");
    handle.update("should not apply");
    handle.succeed("should not apply");
    const t = toastStore.getSnapshot().toasts[0];
    expect(t.status).toBe("error");
    expect(t.title).toBe("Task");
  });
});
