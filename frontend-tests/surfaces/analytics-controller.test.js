import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsController } from "../../static/js/surfaces/focused-analytics-controller.js";

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
    expect(fixture.detailRequests.dispose).toHaveBeenCalledOnce();
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
    expect(parameters.api.get).toHaveBeenCalledWith(
      "analytics/parameters?model=&min_n=10&view=summary",
      expect.any(Object),
    );

    const combinations = createFixture({ section: "combinations" });
    await combinations.controller.start();
    expect(combinations.minimumSamples.value).toBe("8");
    expect(combinations.api.get).toHaveBeenCalledWith(
      "analytics/combinations?model=&min_n=8&view=prompt",
      expect.any(Object),
    );
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

  it("loads only the selected analytics view and focused composition details", async () => {
    const fixture = createFixture({
      section: "parameters",
      search: "?view=values&parameter=cfg",
    });
    await fixture.controller.start();
    expect(fixture.api.get).toHaveBeenLastCalledWith(
      "analytics/parameters?model=&min_n=10&view=values&parameter=cfg",
      expect.any(Object),
    );

    const checkpoint = document.createElement("button");
    checkpoint.dataset.analyticsView = "values";
    checkpoint.dataset.analyticsParameter = "checkpoint";
    fixture.report.append(checkpoint);
    checkpoint.click();
    await settle();
    expect(fixture.api.get).toHaveBeenLastCalledWith(
      "analytics/parameters?model=&min_n=10&view=values&parameter=checkpoint",
      expect.any(Object),
    );
    expect(fixture.requests.cancelRequests).toHaveBeenCalled();

    const details = document.createElement("button");
    details.dataset.compositionDetails = "composition a";
    fixture.report.append(details);
    details.click();
    await settle();
    expect(fixture.api.get).toHaveBeenLastCalledWith(
      "analytics/combinations/composition%20a/render-setups?model=&min_n=1",
      expect.any(Object),
    );
    expect(fixture.view.renderCompositionSetups).toHaveBeenCalledWith(
      "composition a",
      { rows: [] },
    );

    const empty = document.createElement("button");
    empty.dataset.compositionDetails = "";
    fixture.report.append(empty);
    empty.click();
    fixture.report.click();
    const textNode = document.createTextNode("plain text");
    fixture.report.append(textNode);
    textNode.dispatchEvent(new Event("click", { bubbles: true }));
  });

  it("surfaces detail failures and ignores aborted detail requests", async () => {
    const failed = createFixture({ detailError: new Error("detail kaputt") });
    await failed.controller.start();
    const button = document.createElement("button");
    button.dataset.compositionDetails = "composition-a";
    failed.report.append(button);
    button.click();
    await settle();
    expect(failed.status.textContent).toBe("detail kaputt");

    const aborted = createFixture({
      detailError: new DOMException("aborted", "AbortError"),
    });
    await aborted.controller.start();
    const abortButton = document.createElement("button");
    abortButton.dataset.compositionDetails = "composition-a";
    aborted.report.append(abortButton);
    abortButton.click();
    await settle();
    expect(aborted.status.textContent).toBe("Analyse geladen");
  });
});

function createFixture(options = {}) {
  const form = document.createElement("form");
  const model = document.createElement("input");
  const minimumSamples = document.createElement("input");
  form.append(model, minimumSamples);
  const status = document.createElement("p");
  const report = document.createElement("section");
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
  const detailRequests = {
    run: vi.fn((operation) =>
      options.detailError
        ? Promise.reject(options.detailError)
        : operation(new AbortController().signal),
    ),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  const view = {
    render: vi.fn(),
    renderCompositionSetups: vi.fn(),
    clear: vi.fn(),
  };
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
      detailRequests,
      view,
      form,
      model,
      minimumSamples,
      report,
      status,
      locationRef,
      historyRef,
    }),
    api,
    requests,
    detailRequests,
    view,
    form,
    model,
    minimumSamples,
    report,
    status,
    historyRef,
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
