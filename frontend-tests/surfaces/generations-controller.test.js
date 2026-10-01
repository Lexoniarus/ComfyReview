import { beforeEach, describe, expect, it, vi } from "vitest";

import { GenerationsController } from "../../static/js/surfaces/generations-controller.js";

describe("GenerationsController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads lifecycle state, selects, reconciles, polls and disposes", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    expect(fixture.api.get).toHaveBeenCalledWith(
      "generations?limit=100",
      expect.any(Object),
    );
    expect(fixture.requests.schedule).toHaveBeenCalled();

    await fixture.controller.select("generation-1");
    expect(fixture.detail.render).toHaveBeenCalledWith(
      expect.objectContaining({ generation_uid: "generation-1" }),
    );
    await fixture.controller.reconcile("generation-1", "prompt-1");
    expect(fixture.api.post).toHaveBeenCalledWith(
      "generations/generation-1/reconcile",
      { prompt_id: "prompt-1" },
      expect.any(Object),
    );

    const poll = fixture.requests.schedule.mock.calls[0][0];
    poll();
    await settle();
    fixture.documentRef.visibilityState = "hidden";
    fixture.documentRef.dispatchEvent(new Event("visibilitychange"));
    fixture.documentRef.visibilityState = "visible";
    fixture.documentRef.dispatchEvent(new Event("visibilitychange"));
    await settle();

    fixture.controller.dispose();
    expect(fixture.requests.dispose).toHaveBeenCalledOnce();
    expect(fixture.list.dispose).toHaveBeenCalledOnce();
    expect(fixture.detail.dispose).toHaveBeenCalledOnce();
  });

  it("uses the selected filter and avoids polling completed pages", async () => {
    const fixture = createFixture({ status: "completed", completedOnly: true });

    await fixture.controller.start();

    expect(fixture.api.get).toHaveBeenCalledWith(
      "generations?limit=100&status=completed",
      expect.any(Object),
    );
    expect(fixture.requests.schedule).not.toHaveBeenCalled();
  });

  it("surfaces read and reconciliation failures while ignoring aborts", async () => {
    const loadFailure = createFixture({ listError: "unknown" });
    await loadFailure.controller.start();
    expect(loadFailure.status.textContent).toBe(
      "Die Anfrage ist fehlgeschlagen.",
    );

    const selectFailure = createFixture({
      detailError: new Error("detail kaputt"),
    });
    await selectFailure.controller.start();
    await selectFailure.controller.select("generation-1");
    expect(selectFailure.status.textContent).toBe("detail kaputt");

    const reconcileFailure = createFixture({
      reconcileError: new Error("abgleich kaputt"),
    });
    await reconcileFailure.controller.start();
    await reconcileFailure.controller.reconcile("generation-1", null);
    expect(reconcileFailure.status.textContent).toBe("abgleich kaputt");

    const aborted = createFixture({
      listError: new DOMException("aborted", "AbortError"),
    });
    await aborted.controller.start();
    expect(aborted.status.textContent).toBe("Generierungen werden geladen …");
  });

  it("ignores stale detail responses after a newer selection", async () => {
    let resolveFirst;
    const first = new Promise((resolve) => {
      resolveFirst = resolve;
    });
    const fixture = createFixture({ firstDetail: first });
    await fixture.controller.start();
    const pending = fixture.controller.select("generation-1");
    await fixture.controller.select("generation-2");
    resolveFirst({ generation_uid: "generation-1" });
    await pending;

    expect(fixture.detail.render).toHaveBeenCalledTimes(1);
    expect(fixture.detail.render).toHaveBeenCalledWith(
      expect.objectContaining({ generation_uid: "generation-2" }),
    );
  });
});

function createFixture(options = {}) {
  const status = document.createElement("p");
  const list = disposable({
    status: vi.fn(() => options.status || ""),
    render: vi.fn(),
    select: vi.fn(),
  });
  const detail = disposable({ render: vi.fn(), clear: vi.fn() });
  const api = {
    get: vi.fn((path) => {
      if (path.startsWith("generations?")) {
        if (options.listError) return Promise.reject(options.listError);
        return Promise.resolve({
          total: 1,
          items: [
            {
              generation_uid: "generation-1",
              status: options.completedOnly ? "completed" : "running",
            },
          ],
        });
      }
      if (options.detailError) return Promise.reject(options.detailError);
      if (path.endsWith("generation-1") && options.firstDetail) {
        return options.firstDetail;
      }
      return Promise.resolve({
        generation_uid: path.endsWith("generation-2")
          ? "generation-2"
          : "generation-1",
      });
    }),
    post: vi.fn(() =>
      options.reconcileError
        ? Promise.reject(options.reconcileError)
        : Promise.resolve({ status: "running" }),
    ),
  };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    schedule: vi.fn(() => 9),
    cancel: vi.fn(),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
  const documentRef = new EventTarget();
  documentRef.visibilityState = "visible";
  return {
    controller: new GenerationsController({
      api,
      list,
      detail,
      requests,
      status,
      documentRef,
      pollInterval: 10,
    }),
    api,
    list,
    detail,
    requests,
    status,
    documentRef,
  };
}

function disposable(methods) {
  return { ...methods, dispose: vi.fn() };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
