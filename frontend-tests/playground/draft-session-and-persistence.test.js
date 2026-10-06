import { afterEach, describe, expect, it, vi } from "vitest";

import { DraftSession } from "../../static/js/playground/draft-session.js";
import { GeneratorStatePersistence } from "../../static/js/playground/generator-state-persistence.js";

describe("DraftSession", () => {
  it("discards a late draft response after invalidation", async () => {
    const requests = requestOwner();
    const session = new DraftSession(requests);
    const pending = deferred();

    const preparation = session.prepare(() => pending.promise);
    expect(session.phase).toBe("preparing");
    session.invalidate();
    pending.resolve({ draft_uid: "stale-draft" });

    await expect(preparation).rejects.toMatchObject({ name: "AbortError" });
    expect(session.phase).toBe("idle");
    expect(session.draftUid).toBe("");
    expect(session.isReady).toBe(false);
  });

  it("never restores an earlier draft when replacement preparation fails", async () => {
    const session = new DraftSession(requestOwner());
    await session.prepare(() => Promise.resolve({ draft_uid: "draft-a" }));
    expect(session.isReady).toBe(true);

    await expect(
      session.prepare(() => Promise.reject(new Error("draft-b failed"))),
    ).rejects.toThrow("draft-b failed");

    expect(session.phase).toBe("idle");
    expect(session.draftUid).toBe("");
    expect(session.isReady).toBe(false);
  });

  it("rejects drafts without a stable server identity", async () => {
    const session = new DraftSession(requestOwner());

    await expect(session.prepare(() => Promise.resolve({}))).rejects.toThrow(
      "keine Draft-ID",
    );
    await expect(session.submit(() => Promise.resolve({}))).rejects.toThrow(
      "nicht mehr gültig",
    );
  });

  it("discards a late submission after its draft changes", async () => {
    const requests = requestOwner();
    const session = new DraftSession(requests);
    await session.prepare(() => Promise.resolve({ draft_uid: "draft-a" }));
    const pending = deferred();

    const submission = session.submit(() => pending.promise);
    expect(session.phase).toBe("submitting");
    session.invalidate();
    pending.resolve({ generation_uid: "stale-generation" });

    await expect(submission).rejects.toMatchObject({ name: "AbortError" });
    expect(session.phase).toBe("idle");
    expect(session.isReady).toBe(false);
  });

  it("owns cancellation and disposal of its request lifecycle", () => {
    const requests = requestOwner();
    const session = new DraftSession(requests);

    session.invalidate();
    session.dispose();

    expect(requests.cancelRequests).toHaveBeenCalledTimes(2);
    expect(requests.dispose).toHaveBeenCalledOnce();
  });
});

describe("GeneratorStatePersistence", () => {
  afterEach(() => vi.useRealTimers());

  it("loads through the shared API boundary", async () => {
    const api = {
      get: vi.fn(() => Promise.resolve({ checkpoint: "saved" })),
      put: vi.fn(),
    };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({}),
    });

    await expect(persistence.load()).resolves.toEqual({ checkpoint: "saved" });
    expect(api.get).toHaveBeenCalledWith("playground/generator-state");
  });

  it("debounces complete snapshots and persists only the latest scheduled state", async () => {
    vi.useFakeTimers();
    let state = { checkpoint: "first" };
    const api = {
      get: vi.fn(),
      put: vi.fn(() => Promise.resolve({})),
    };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({ ...state }),
      delay: 50,
    });

    persistence.schedule();
    state = { checkpoint: "latest" };
    persistence.schedule();
    await vi.advanceTimersByTimeAsync(50);
    await persistence.writeTail;

    expect(api.put).toHaveBeenCalledOnce();
    expect(api.put).toHaveBeenCalledWith(
      "playground/generator-state",
      { checkpoint: "latest" },
      { keepalive: false },
    );
  });

  it("serializes writes so an older response cannot overwrite a newer state", async () => {
    const first = deferred();
    const second = deferred();
    const api = {
      get: vi.fn(),
      put: vi
        .fn()
        .mockImplementationOnce(() => first.promise)
        .mockImplementationOnce(() => second.promise),
    };
    let state = { checkpoint: "first" };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({ ...state }),
    });

    const firstSave = persistence.save();
    await settle();
    state = { checkpoint: "latest" };
    const latestSave = persistence.save();
    expect(api.put).toHaveBeenCalledOnce();

    first.resolve({});
    await firstSave;
    await settle();
    expect(api.put).toHaveBeenNthCalledWith(
      2,
      "playground/generator-state",
      { checkpoint: "latest" },
      { keepalive: false },
    );
    second.resolve({});
    await latestSave;
  });

  it("continues with a newer write after an earlier save fails", async () => {
    const api = {
      get: vi.fn(),
      put: vi
        .fn()
        .mockRejectedValueOnce(new Error("old save failed"))
        .mockResolvedValueOnce({}),
    };
    let state = { checkpoint: "old" };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({ ...state }),
    });

    const oldSave = persistence.save();
    state = { checkpoint: "new" };
    const newSave = persistence.save();

    await expect(oldSave).rejects.toThrow("old save failed");
    await expect(newSave).resolves.toEqual({});
    expect(api.put).toHaveBeenLastCalledWith(
      "playground/generator-state",
      { checkpoint: "new" },
      { keepalive: false },
    );
  });

  it("flushes the newest state with keepalive and cancels the debounce", async () => {
    vi.useFakeTimers();
    const api = {
      get: vi.fn(),
      put: vi.fn(() => Promise.resolve({})),
    };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({ checkpoint: "leaving" }),
      delay: 50,
    });

    persistence.schedule();
    await persistence.flush();
    await vi.advanceTimersByTimeAsync(50);

    expect(api.put).toHaveBeenCalledOnce();
    expect(api.put).toHaveBeenCalledWith(
      "playground/generator-state",
      { checkpoint: "leaving" },
      { keepalive: true },
    );
  });

  it("ignores schedules after disposal and only waits for the existing tail", async () => {
    vi.useFakeTimers();
    const api = {
      get: vi.fn(),
      put: vi.fn(() => Promise.reject(new Error("save failed"))),
    };
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({ checkpoint: "disposed" }),
      delay: 10,
    });

    persistence.schedule();
    await vi.advanceTimersByTimeAsync(10);
    await expect(persistence.writeTail).rejects.toThrow("save failed");
    persistence.dispose();
    persistence.schedule();
    await expect(persistence.flush()).rejects.toThrow("save failed");
    expect(api.put).toHaveBeenCalledOnce();
  });
});

function requestOwner() {
  return {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
}

function deferred() {
  /** @type {(value: any) => void} */
  let resolve;
  /** @type {(reason?: unknown) => void} */
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
}
