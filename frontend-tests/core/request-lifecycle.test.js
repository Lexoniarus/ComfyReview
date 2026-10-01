import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";

describe("RequestLifecycle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("runs one request and releases its controller", async () => {
    const lifecycle = new RequestLifecycle();

    await expect(lifecycle.run(async (signal) => signal.aborted)).resolves.toBe(
      false,
    );
    expect(lifecycle.controllers.size).toBe(0);
  });

  it("aborts in-flight work when disposed", async () => {
    const lifecycle = new RequestLifecycle();
    let observedSignal;
    const pending = lifecycle.run(
      (signal) =>
        new Promise((resolve) => {
          observedSignal = signal;
          signal.addEventListener("abort", () => resolve("aborted"));
        }),
    );

    lifecycle.dispose();

    await expect(pending).resolves.toBe("aborted");
    expect(observedSignal.aborted).toBe(true);
    lifecycle.dispose();
  });

  it("cancels active requests while remaining reusable", async () => {
    const lifecycle = new RequestLifecycle();
    const pending = lifecycle.run(
      (signal) =>
        new Promise((resolve) => {
          signal.addEventListener("abort", () => resolve("aborted"));
        }),
    );

    lifecycle.cancelRequests();

    await expect(pending).resolves.toBe("aborted");
    await expect(lifecycle.run(async () => "next")).resolves.toBe("next");
  });

  it("owns scheduled callbacks and cancellation", () => {
    const lifecycle = new RequestLifecycle();
    const callback = vi.fn();
    const first = lifecycle.schedule(callback, 20);
    const second = lifecycle.schedule(callback, 30);

    lifecycle.cancel(first);
    lifecycle.cancel(null);
    vi.advanceTimersByTime(25);
    expect(callback).not.toHaveBeenCalled();
    vi.advanceTimersByTime(5);
    expect(callback).toHaveBeenCalledOnce();
    expect(lifecycle.timers.size).toBe(0);

    lifecycle.cancel(second);
  });

  it("clears timers and rejects new work after disposal", async () => {
    const lifecycle = new RequestLifecycle();
    const callback = vi.fn();
    lifecycle.schedule(callback, 20);
    lifecycle.dispose();

    vi.runAllTimers();
    expect(callback).not.toHaveBeenCalled();
    expect(lifecycle.schedule(callback, 20)).toBeNull();
    await expect(lifecycle.run(async () => true)).rejects.toMatchObject({
      name: "AbortError",
    });
  });
});
