import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsCollectionController } from "../../static/js/analytics/analytics-collection-controller.js";

describe("AnalyticsCollectionController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads one deduplicated page and disconnects at the end", async () => {
    const fixture = createFixture();
    const appendPage = vi.fn();
    fixture.controller.start(
      { items: [{ component_uid: "one" }], offset: 0, total: 3 },
      fixture.sentinel,
      {
        fetchPage: vi.fn(() =>
          Promise.resolve({
            items: [{ component_uid: "one" }, { component_uid: "two" }],
            offset: 1,
            total: 3,
          }),
        ),
        appendPage,
      },
    );

    fixture.intersect();
    await settle();

    expect(appendPage).toHaveBeenCalledWith({
      items: [{ component_uid: "two" }],
      offset: 1,
      total: 3,
    });
    expect(fixture.status.textContent).toContain("3 von 3");
    expect(fixture.observer.disconnect).toHaveBeenCalled();
  });

  it("disconnects immediately after a directly loaded final page", async () => {
    const fixture = createFixture();
    fixture.controller.start(
      { items: [], offset: 0, total: 1 },
      fixture.sentinel,
      {
        fetchPage: vi.fn(() =>
          Promise.resolve({
            items: [{ composition_uid: "final" }],
            offset: 0,
            total: 1,
          }),
        ),
        appendPage: vi.fn(),
      },
    );
    await fixture.controller.loadNext();
    expect(fixture.observer.disconnect).toHaveBeenCalledOnce();
  });

  it("resets stale requests and never appends after dispose", async () => {
    const fixture = createFixture();
    let resolvePage;
    const page = new Promise((resolve) => {
      resolvePage = resolve;
    });
    const appendPage = vi.fn();
    fixture.controller.start(
      { items: [], offset: 0, total: 1 },
      fixture.sentinel,
      { fetchPage: vi.fn(() => page), appendPage },
    );
    const pending = fixture.controller.loadNext();
    fixture.controller.dispose();
    resolvePage({ items: [{ setup_key: "late" }], offset: 0, total: 1 });
    await pending;

    expect(appendPage).not.toHaveBeenCalled();
    expect(fixture.requests.cancelRequests).toHaveBeenCalled();
    expect(fixture.requests.dispose).toHaveBeenCalled();
  });

  it("offers an accessible retry after a failed page", async () => {
    const fixture = createFixture();
    const fetchPage = vi
      .fn()
      .mockRejectedValueOnce(new Error("Seite kaputt"))
      .mockResolvedValueOnce({
        items: [{ parameter: "cfg", value: "6" }],
        offset: 0,
        total: 1,
      });
    const appendPage = vi.fn();
    fixture.controller.start(
      { items: [], offset: 0, total: 1 },
      fixture.sentinel,
      { fetchPage, appendPage },
    );

    await fixture.controller.loadNext();
    expect(fixture.status.textContent).toBe("Seite kaputt");
    const retry = document.querySelector(".analytics-retry");
    expect(retry?.textContent).toBe("Erneut versuchen");
    retry.click();
    await settle();
    expect(appendPage).toHaveBeenCalledOnce();

    fixture.controller.reset();
    await fixture.controller.loadNext();
  });

  it("uses fallback values for malformed pages and failures", async () => {
    const fixture = createFixture();
    const appendPage = vi.fn();
    fixture.controller.start(
      { items: [{}], offset: "not-a-number", total: 2 },
      fixture.sentinel,
      {
        fetchPage: vi
          .fn()
          .mockRejectedValueOnce("failed")
          .mockResolvedValueOnce({ items: [{}], offset: 1, total: 2 }),
        appendPage,
      },
    );
    await fixture.controller.loadNext();
    expect(fixture.status.textContent).toContain("konnten nicht geladen");
    document.querySelector(".analytics-retry")?.click();
    await settle();
    expect(appendPage).toHaveBeenCalledWith({
      items: [],
      offset: 1,
      total: 2,
    });
  });

  it("ignores abort errors and intersections without more pages", async () => {
    const fixture = createFixture();
    fixture.controller.start(
      { items: [], offset: 0, total: 1 },
      fixture.sentinel,
      {
        fetchPage: vi.fn(() =>
          Promise.reject(new DOMException("aborted", "AbortError")),
        ),
        appendPage: vi.fn(),
      },
    );
    fixture.intersect(false);
    await fixture.controller.loadNext();
    expect(document.querySelector(".analytics-retry")).toBeNull();

    fixture.controller.start(
      { items: [{ composition_uid: "done" }], offset: 0, total: 1 },
      fixture.sentinel,
      { fetchPage: vi.fn(), appendPage: vi.fn() },
    );
    await fixture.controller.loadNext();
    expect(fixture.observer.observe).toHaveBeenCalledTimes(1);
  });

  it("uses the browser observer boundary by default", () => {
    const observe = vi.fn();
    const disconnect = vi.fn();
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        constructor(callback, options) {
          expect(callback).toBeTypeOf("function");
          expect(options).toEqual({ rootMargin: "600px" });
        }

        observe(element) {
          observe(element);
        }

        disconnect() {
          disconnect();
        }
      },
    );
    const status = document.createElement("p");
    const sentinel = document.createElement("div");
    const requests = {
      run: vi.fn(),
      cancelRequests: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new AnalyticsCollectionController({ requests, status });
    controller.start({ items: [], total: 2 }, sentinel, {
      fetchPage: vi.fn(),
      appendPage: vi.fn(),
    });
    expect(observe).toHaveBeenCalledWith(sentinel);
    controller.reset();
    expect(disconnect).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

function createFixture() {
  const status = document.createElement("p");
  const sentinel = document.createElement("div");
  document.body.append(status, sentinel);
  let callback = () => {};
  const observer = { observe: vi.fn(), disconnect: vi.fn() };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  const controller = new AnalyticsCollectionController({
    requests,
    status,
    observerFactory: (value) => {
      callback = value;
      return observer;
    },
  });
  return {
    controller,
    requests,
    status,
    sentinel,
    observer,
    intersect: (isIntersecting = true) => callback([{ isIntersecting }]),
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
