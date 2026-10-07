import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { TopWorstController } from "../../static/js/surfaces/top-worst-controller.js";

const initialState = {
  scopes: ["character-a"],
  classification: "classified",
  model: "anime",
  checkpoint: "base",
  setKey: "favorite",
  mode: "top",
  offset: 48,
};

describe("TopWorstController", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("loads facets and rankings, selects an image, and owns actions", async () => {
    const fixture = createFixture();
    fixture.controller.start();
    await settle();

    expect(fixture.api.get).toHaveBeenCalledWith(
      expect.stringContaining("rankings?scope=character-a"),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(fixture.navigator.render).toHaveBeenCalled();
    expect(fixture.activeScopes.render).toHaveBeenCalled();
    expect(fixture.grid.render).toHaveBeenCalledWith(
      [{ image_uid: "image-1" }],
      48,
    );
    expect(fixture.root.querySelector("[data-result-count]")?.textContent).toBe(
      "1 bewertetes Bild",
    );
    expect(fixture.pagination.render).toHaveBeenCalledWith(1, 48, 48);

    await fixture.controller.selectImage("image/1");
    expect(fixture.api.get).toHaveBeenCalledWith(
      "images/image%2F1",
      expect.any(Object),
    );
    expect(fixture.inspector.render).toHaveBeenCalledWith({
      image_uid: "image/1",
    });
    expect(fixture.rails.open).toHaveBeenCalledWith("inspector");
    await fixture.controller.selectImage("image/1");
    expect(fixture.rails.close).toHaveBeenCalledWith("inspector");
    await fixture.controller.refresh("image/1");
    expect(fixture.grid.render).toHaveBeenCalledTimes(2);
    fixture.rails.open("scope");
    fixture.root.querySelector("[data-scope-navigator]")?.click();
    fixture.root.querySelector("[data-rail-action]")?.click();
    fixture.root.click();
    expect(fixture.rails.close).toHaveBeenCalledWith("scope");
    fixture.rails.open("inspector");
    fixture.root.querySelector("[data-image-inspector]")?.click();
    fixture.root.querySelector("[data-rail-action]")?.click();
    fixture.root.querySelector("[data-image-action='select']")?.click();
    fixture.root.click();
    expect(fixture.rails.close).toHaveBeenCalledWith("inspector");
    await fixture.controller.reload();
    expect(fixture.grid.render).toHaveBeenCalledTimes(3);
    expect(fixture.inspector.empty).toHaveBeenCalledOnce();

    fixture.root.querySelector("[data-surface-action='worst']")?.click();
    fixture.root.click();
    const textTarget = document.createTextNode("text target");
    fixture.root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    const unknown = document.createElement("button");
    unknown.dataset.surfaceAction = "unknown";
    fixture.root.append(unknown);
    unknown.click();
    expect(fixture.state.update).toHaveBeenCalledWith({ mode: "worst" });
    fixture.controller.dispose();
    expect(fixture.unsubscribe).toHaveBeenCalledOnce();
    expect(fixture.state.dispose).toHaveBeenCalledOnce();
    expect(fixture.activeScopes.dispose).toHaveBeenCalledOnce();
    expect(fixture.pagination.dispose).toHaveBeenCalledOnce();
    expect(fixture.rails.dispose).toHaveBeenCalledOnce();
    expect(fixture.inspector.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces request errors but ignores aborted work", async () => {
    const failing = createFixture({ rankingError: new Error("kaputt") });
    failing.controller.start();
    await settle();
    expect(failing.grid.error).toHaveBeenCalledWith("kaputt");

    failing.api.get.mockRejectedValueOnce("unknown");
    await failing.controller.selectImage("image-1");
    expect(failing.inspector.error).toHaveBeenCalledWith(
      "Die Anfrage ist fehlgeschlagen.",
    );

    failing.api.get.mockRejectedValueOnce(
      new DOMException("aborted", "AbortError"),
    );
    await failing.controller.selectImage("image-2");
    expect(failing.inspector.error).toHaveBeenCalledOnce();

    const aborted = createFixture({
      rankingError: new DOMException("aborted", "AbortError"),
    });
    aborted.controller.start();
    await settle();
    expect(aborted.grid.error).not.toHaveBeenCalled();

    const idle = createFixture();
    await idle.controller.refresh("image-1");
    await idle.controller.reload();
    expect(idle.api.get).not.toHaveBeenCalled();
  });
});

function createFixture(options = {}) {
  const root = document.createElement("main");
  root.insertAdjacentHTML(
    "beforeend",
    "<button data-surface-action='top'></button>" +
      "<button data-surface-action='worst'></button>" +
      "<button data-rail-action='scope'></button>" +
      "<button data-image-action='select' data-image-uid='image-1'></button>" +
      "<aside data-scope-navigator></aside>" +
      "<aside data-image-inspector></aside>" +
      "<span data-result-count></span>",
  );
  document.body.append(root);
  let listener = null;
  const unsubscribe = vi.fn();
  const state = {
    subscribe: vi.fn((callback) => {
      listener = callback;
      return unsubscribe;
    }),
    start: vi.fn(() => listener(initialState)),
    update: vi.fn(),
    dispose: vi.fn(),
  };
  const api = {
    get: vi.fn((path) => {
      if (path.startsWith("scopes/")) return Promise.resolve({ facets: [] });
      if (path.startsWith("rankings")) {
        return options.rankingError
          ? Promise.reject(options.rankingError)
          : Promise.resolve({
              items: [{ image_uid: "image-1" }],
              offset: 48,
              limit: 48,
              total: 1,
            });
      }
      return Promise.resolve({ image_uid: decodeURIComponent(path.slice(7)) });
    }),
  };
  const navigator = { render: vi.fn(), dispose: vi.fn() };
  const activeScopes = { render: vi.fn(), dispose: vi.fn() };
  const grid = {
    loading: vi.fn(),
    render: vi.fn(),
    error: vi.fn(),
    empty: vi.fn(),
    dispose: vi.fn(),
  };
  const inspector = {
    loading: vi.fn(),
    render: vi.fn(),
    error: vi.fn(),
    empty: vi.fn(),
    dispose: vi.fn(),
  };
  const viewer = { dispose: vi.fn() };
  const openRails = new Set();
  const rails = {
    open: vi.fn((rail) => {
      openRails.clear();
      openRails.add(rail);
    }),
    close: vi.fn((rail) => {
      openRails.delete(rail);
    }),
    isOpen: vi.fn((rail) => openRails.has(rail)),
    isDrawerMode: vi.fn(() => true),
    dispose: vi.fn(),
  };
  const pagination = { render: vi.fn(), dispose: vi.fn() };
  const controller = new TopWorstController({
    api,
    state,
    navigator,
    activeScopes,
    grid,
    pagination,
    inspector,
    viewer,
    rails,
    facetRequests: new RequestLifecycle(),
    rankingRequests: new RequestLifecycle(),
    contextRequests: new RequestLifecycle(),
    root,
  });
  return {
    controller,
    api,
    state,
    navigator,
    activeScopes,
    pagination,
    rails,
    grid,
    inspector,
    root,
    unsubscribe,
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
