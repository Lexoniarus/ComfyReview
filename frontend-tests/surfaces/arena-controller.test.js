import { describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { ArenaController } from "../../static/js/surfaces/arena-controller.js";

const stateValue = {
  scopes: ["character-a"],
  classification: "classified",
  model: "anime",
  checkpoint: "base",
  setKey: "favorite",
  mode: "top",
  offset: 0,
};

describe("ArenaController", () => {
  it("loads a pair, records a UID decision, and disposes", async () => {
    const fixture = createFixture();
    fixture.controller.start();
    await settle();
    expect(fixture.board.render).toHaveBeenCalled();

    await fixture.controller.recordDecision("right");
    expect(fixture.api.post).toHaveBeenCalledWith(
      "arena/decisions",
      {
        left_image_uid: "left",
        right_image_uid: "right",
        winner_side: "right",
      },
      expect.any(Object),
    );
    fixture.controller.inspect({ image_uid: "right" });
    expect(fixture.rails.open).toHaveBeenCalledWith("inspector");
    fixture.controller.expand("/right.png");
    expect(fixture.viewer.open).toHaveBeenCalledWith("/right.png");
    await fixture.controller.refresh("right");
    expect(fixture.board.render).toHaveBeenCalledTimes(3);

    fixture.controller.dispose();
    expect(fixture.unsubscribe).toHaveBeenCalledOnce();
    expect(fixture.keyboard.dispose).toHaveBeenCalledOnce();
    expect(fixture.inspector.dispose).toHaveBeenCalledOnce();
  });

  it("handles empty, failed, aborted, and idle operations", async () => {
    const empty = createFixture({ pair: null });
    empty.controller.start();
    await settle();
    expect(empty.board.empty).toHaveBeenCalledOnce();

    const failing = createFixture({ mutationError: new Error("kaputt") });
    failing.controller.start();
    await settle();
    await failing.controller.recordDecision("left");
    expect(failing.status.textContent).toBe("kaputt");

    const refreshFailure = createFixture();
    refreshFailure.controller.start();
    await settle();
    refreshFailure.api.get.mockRejectedValueOnce(new Error("refresh kaputt"));
    await refreshFailure.controller.refresh("left");
    expect(refreshFailure.inspector.error).toHaveBeenCalledWith(
      "refresh kaputt",
    );
    expect(refreshFailure.status.textContent).toBe(
      "Aktualisierung fehlgeschlagen",
    );

    const readError = createFixture({ readError: "unknown" });
    readError.controller.start();
    await settle();
    expect(readError.board.error).toHaveBeenCalledWith(
      "Die Anfrage ist fehlgeschlagen.",
    );

    const aborted = createFixture({
      readError: new DOMException("aborted", "AbortError"),
    });
    aborted.controller.start();
    await settle();
    expect(aborted.board.error).not.toHaveBeenCalled();

    const idle = createFixture();
    await idle.controller.refresh("left");
    await idle.controller.recordDecision("left");
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
    start: vi.fn(() => listener(stateValue)),
    dispose: vi.fn(),
  };
  const pair =
    options.pair === undefined
      ? {
          left: { image_uid: "left", image_url: "/left.png" },
          right: { image_uid: "right", image_url: "/right.png" },
        }
      : options.pair;
  const api = {
    get: vi.fn((path) => {
      if (options.readError) return Promise.reject(options.readError);
      if (path.startsWith("scopes/")) return Promise.resolve({ facets: [] });
      if (path.startsWith("images/")) {
        return Promise.resolve({
          image_uid: decodeURIComponent(path.slice(7)),
        });
      }
      return Promise.resolve(pair);
    }),
    post: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve({}),
    ),
  };
  const navigator = disposable({ render: vi.fn() });
  const activeScopes = disposable({ render: vi.fn() });
  const board = disposable({
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
    dispose: vi.fn(),
  };
  const viewer = disposable({ open: vi.fn() });
  const rails = disposable({ open: vi.fn() });
  const keyboard = disposable({});
  const status = document.createElement("span");
  const controller = new ArenaController({
    api,
    state,
    navigator,
    activeScopes,
    board,
    inspector,
    viewer,
    rails,
    keyboard,
    readRequests: new RequestLifecycle(),
    mutationRequests: new RequestLifecycle(),
    status,
  });
  return {
    controller,
    api,
    board,
    viewer,
    rails,
    keyboard,
    inspector,
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
