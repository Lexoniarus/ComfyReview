import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { ReviewController } from "../../static/js/surfaces/review-controller.js";

const initialState = {
  scopes: ["character-a"],
  classification: "classified",
  model: "anime",
  checkpoint: "base",
  setKey: "favorite",
  mode: "top",
  offset: 0,
};

describe("ReviewController", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("loads, rates, deletes after confirmation, and disposes collaborators", async () => {
    const fixture = createFixture();
    fixture.controller.start();
    await settle();
    expect(fixture.stage.render).toHaveBeenCalledWith(
      expect.objectContaining({ image_uid: "image-1" }),
    );
    expect(fixture.navigator.render).toHaveBeenCalled();
    expect(fixture.activeScopes.render).toHaveBeenCalled();

    await fixture.controller.submitRating(9);
    expect(fixture.api.post).toHaveBeenCalledWith(
      "reviews",
      { image_uid: "image-1", rating: 9 },
      expect.any(Object),
    );

    await fixture.controller.deleteCurrent();
    expect(fixture.dialog.confirm).toHaveBeenCalledOnce();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "images/image-1/delete",
      {},
      expect.any(Object),
    );
    fixture.controller.expand("/files/image.png");
    expect(fixture.viewer.open).toHaveBeenCalledWith("/files/image.png");

    fixture.controller.dispose();
    expect(fixture.unsubscribe).toHaveBeenCalledOnce();
    expect(fixture.keyboard.dispose).toHaveBeenCalledOnce();
    expect(fixture.rails.dispose).toHaveBeenCalledOnce();
  });

  it("handles empty, rejected, failed, aborted, and duplicate work", async () => {
    const empty = createFixture({ candidate: null });
    empty.controller.start();
    await settle();
    expect(empty.stage.empty).toHaveBeenCalledOnce();

    const rejected = createFixture({ confirmed: false });
    rejected.controller.start();
    await settle();
    await rejected.controller.deleteCurrent();
    expect(rejected.api.post).not.toHaveBeenCalled();

    const failing = createFixture({ mutationError: new Error("kaputt") });
    failing.controller.start();
    await settle();
    await failing.controller.submitRating(8);
    expect(failing.status.textContent).toBe("kaputt");
    expect(failing.stage.setBusy).toHaveBeenLastCalledWith(false);

    const loadingError = createFixture({ readError: "unknown" });
    loadingError.controller.start();
    await settle();
    expect(loadingError.stage.error).toHaveBeenCalledWith(
      "Die Anfrage ist fehlgeschlagen.",
    );

    const aborted = createFixture({
      readError: new DOMException("aborted", "AbortError"),
    });
    aborted.controller.start();
    await settle();
    expect(aborted.stage.error).not.toHaveBeenCalled();

    const idle = createFixture();
    await idle.controller.submitRating(4);
    await idle.controller.deleteCurrent();
    expect(idle.api.post).not.toHaveBeenCalled();
  });
});

function createFixture(options = {}) {
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
  const candidate =
    options.candidate === undefined
      ? { image_uid: "image-1", image_url: "/files/image.png" }
      : options.candidate;
  const api = {
    get: vi.fn((path) => {
      if (options.readError) return Promise.reject(options.readError);
      if (path.startsWith("scopes/")) return Promise.resolve({ facets: [] });
      return Promise.resolve(candidate);
    }),
    post: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve({}),
    ),
  };
  const navigator = disposable({ render: vi.fn() });
  const activeScopes = disposable({ render: vi.fn() });
  const stage = disposable({
    loading: vi.fn(),
    render: vi.fn(),
    empty: vi.fn(),
    error: vi.fn(),
    setBusy: vi.fn(),
  });
  const inspector = {
    render: vi.fn(),
    empty: vi.fn(),
    error: vi.fn(),
  };
  const viewer = disposable({ open: vi.fn() });
  const rails = disposable({ open: vi.fn() });
  const dialog = disposable({
    confirm: vi.fn(() => Promise.resolve(options.confirmed !== false)),
  });
  const keyboard = disposable({});
  const status = document.createElement("span");
  const controller = new ReviewController({
    api,
    state,
    navigator,
    activeScopes,
    stage,
    inspector,
    viewer,
    rails,
    dialog,
    keyboard,
    readRequests: new RequestLifecycle(),
    mutationRequests: new RequestLifecycle(),
    status,
  });
  return {
    controller,
    api,
    navigator,
    activeScopes,
    stage,
    viewer,
    rails,
    dialog,
    keyboard,
    status,
    unsubscribe,
  };
}

function disposable(methods) {
  return { ...methods, dispose: vi.fn() };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
