import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsController } from "../../static/js/surfaces/analytics-controller.js";

describe("AnalyticsController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("restores report filters, loads and owns URL updates", async () => {
    const fixture = createFixture({
      section: "scopes",
      search: "?model=anime&min_n=6",
    });

    await fixture.controller.start();
    expect(fixture.api.get).toHaveBeenCalledWith(
      "analytics/scopes?model=anime&min_n=6",
      expect.any(Object),
    );
    fixture.minimumSamples.value = "-2";
    fixture.form.dispatchEvent(new Event("submit", { cancelable: true }));
    await settle();
    expect(fixture.historyRef.replaceState).toHaveBeenCalledWith(
      null,
      "",
      "/prompt_tokens?model=anime&min_n=0",
    );
    fixture.controller.dispose();
    expect(fixture.requests.dispose).toHaveBeenCalledOnce();
    expect(fixture.view.clear).toHaveBeenCalled();
  });

  it("uses section defaults and falls back to overview", async () => {
    const overview = createFixture({ section: "unknown" });
    await overview.controller.start();
    expect(overview.minimumSamples.value).toBe("5");
    expect(overview.api.get).toHaveBeenCalledWith(
      "analytics/overview?model=&min_n=5",
      expect.any(Object),
    );

    const parameters = createFixture({ section: "parameters" });
    await parameters.controller.start();
    expect(parameters.minimumSamples.value).toBe("10");

    const combinations = createFixture({ section: "combinations" });
    await combinations.controller.start();
    expect(combinations.minimumSamples.value).toBe("8");
  });

  it("surfaces failures, normalizes invalid input and ignores aborts", async () => {
    const failed = createFixture({ error: new Error("kaputt") });
    await failed.controller.start();
    expect(failed.status.textContent).toBe("kaputt");

    const unknown = createFixture({ error: "kaputt" });
    await unknown.controller.start();
    expect(unknown.status.textContent).toContain("nicht geladen");

    const aborted = createFixture({
      error: new DOMException("aborted", "AbortError"),
    });
    await aborted.controller.start();
    expect(aborted.status.textContent).toBe("Analyse wird geladen …");

    const invalid = createFixture();
    await invalid.controller.start();
    invalid.minimumSamples.value = "invalid";
    invalid.form.dispatchEvent(new Event("submit", { cancelable: true }));
    await settle();
    expect(invalid.api.get).toHaveBeenLastCalledWith(
      "analytics/overview?model=&min_n=0",
      expect.any(Object),
    );
  });
});

function createFixture(options = {}) {
  const form = document.createElement("form");
  const model = document.createElement("input");
  const minimumSamples = document.createElement("input");
  form.append(model, minimumSamples);
  const status = document.createElement("p");
  const api = {
    get: vi.fn(() =>
      options.error
        ? Promise.reject(options.error)
        : Promise.resolve({ rows: [] }),
    ),
  };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  const view = { render: vi.fn(), clear: vi.fn() };
  const locationRef = {
    search: options.search || "",
    pathname: "/prompt_tokens",
  };
  const historyRef = { replaceState: vi.fn() };
  return {
    controller: new AnalyticsController({
      section: options.section || "overview",
      api,
      requests,
      view,
      form,
      model,
      minimumSamples,
      status,
      locationRef,
      historyRef,
    }),
    api,
    requests,
    view,
    form,
    model,
    minimumSamples,
    status,
    historyRef,
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
