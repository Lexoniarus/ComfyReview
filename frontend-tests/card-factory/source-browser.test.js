import { beforeEach, describe, expect, it, vi } from "vitest";

import { CardSourceBrowser } from "../../static/js/card-factory/source-browser.js";

describe("CardSourceBrowser", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <main data-card-factory-sources>
        <span data-card-factory-status></span>
        <section data-card-source-grid></section>
        <button data-source-previous></button>
        <span data-source-page></span>
        <button data-source-next></button>
      </main>`;
  });

  it("loads, pages, reserves a group and disposes", async () => {
    const fixture = createFixture();
    await fixture.browser.start();
    expect(document.querySelectorAll(".card-source-item")).toHaveLength(1);
    document.querySelector("[data-source-next]").click();
    await settle();
    expect(fixture.api.sources).toHaveBeenLastCalledWith(
      expect.objectContaining({ offset: 1, limit: 1 }),
    );
    document.querySelector("[data-source-previous]").click();
    await settle();
    document.querySelector(".card-source-item").click();
    await settle();
    expect(fixture.locationRef.assign).toHaveBeenCalledWith(
      "/card-candidate-groups",
    );
    fixture.browser.dispose();
    expect(fixture.requests.dispose).toHaveBeenCalledOnce();
  });

  it("renders empty pages and readable load/create failures", async () => {
    const empty = createFixture({ empty: true });
    await empty.browser.start();
    expect(document.querySelector(".card-empty-state").textContent).toContain(
      "Keine zugänglichen",
    );

    const failed = createFixture({ loadError: new Error("offline") });
    await failed.browser.start();
    expect(document.querySelector(".card-error-state").textContent).toBe(
      "offline",
    );

    document.body.innerHTML = `
      <main data-card-factory-sources><span data-card-factory-status></span><section data-card-source-grid></section><button data-source-previous></button><span data-source-page></span><button data-source-next></button></main>`;
    const createFailed = createFixture({ createError: "bad" });
    await createFailed.browser.start();
    document.querySelector(".card-source-item").click();
    await settle();
    expect(
      document.querySelector("[data-card-factory-status]").textContent,
    ).toBe("Die Anfrage ist fehlgeschlagen.");
  });

  it("rejects incomplete source shells", () => {
    document.querySelector("[data-source-next]").remove();
    expect(() => createFixture()).toThrow("Missing [data-source-next]");
    document.body.innerHTML = `
      <main data-card-factory-sources><section data-card-source-grid></section><button data-source-previous></button><span data-source-page></span><button data-source-next></button></main>`;
    expect(() => createFixture()).toThrow("Missing [data-card-factory-status]");
  });

  it("quietly ignores aborted source and create requests", async () => {
    const loadAborted = createFixture({
      loadError: new DOMException("aborted", "AbortError"),
    });
    await loadAborted.browser.start();
    expect(document.querySelector(".card-error-state")).toBeNull();

    document.body.innerHTML = `
      <main data-card-factory-sources><span data-card-factory-status></span><section data-card-source-grid></section><button data-source-previous></button><span data-source-page></span><button data-source-next></button></main>`;
    const createAborted = createFixture({
      createError: new DOMException("aborted", "AbortError"),
    });
    await createAborted.browser.start();
    document.querySelector(".card-source-item").click();
    await settle();
    expect(document.querySelector(".card-source-item").disabled).toBe(false);
  });
});

function createFixture(options = {}) {
  const api = {
    sources: vi.fn(({ offset }) => {
      if (options.loadError) return Promise.reject(options.loadError);
      return Promise.resolve({
        total: options.empty ? 0 : 2,
        items: options.empty
          ? []
          : [{ image_uid: `image-${offset + 1}`, image_url: "/image.png" }],
      });
    }),
    createGroup: vi.fn(() =>
      options.createError
        ? Promise.reject(options.createError)
        : Promise.resolve({ group_id: "group-1" }),
    ),
  };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  const locationRef = { assign: vi.fn() };
  return {
    browser: new CardSourceBrowser({
      root: document.querySelector("[data-card-factory-sources]"),
      api,
      requests,
      locationRef,
      pageSize: 1,
    }),
    api,
    requests,
    locationRef,
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
