import { describe, expect, it, vi } from "vitest";

import { ImageContentLevelController } from "../../static/js/content/image-content-level-controller.js";

describe("ImageContentLevelController", () => {
  it("assigns and removes audited overrides through the API", async () => {
    const fixture = createFixture();

    await fixture.controller.assign("image/1", "nude");
    expect(fixture.api.put).toHaveBeenCalledWith(
      "images/image%2F1/content-level",
      { content_level: "nude" },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(fixture.onChanged).toHaveBeenCalledWith("image/1");
    expect(fixture.inspector.setContentLevelBusy.mock.calls).toEqual([
      [true],
      [false],
    ]);

    await fixture.controller.assign("image/1", null);
    expect(fixture.api.put).toHaveBeenLastCalledWith(
      "images/image%2F1/content-level",
      { content_level: null },
      expect.any(Object),
    );
  });

  it("reports assignment failures, ignores aborts, and blocks overlap", async () => {
    const pending = deferred();
    const fixture = createFixture();
    fixture.api.put.mockReturnValueOnce(pending.promise);
    const first = fixture.controller.assign("image-1", "sexy");
    await fixture.controller.assign("image-2", "lewd");
    expect(fixture.api.put).toHaveBeenCalledOnce();
    pending.resolve({});
    await first;

    fixture.api.put.mockRejectedValueOnce(new Error("kaputt"));
    await fixture.controller.assign("image-1", "explicit");
    expect(fixture.inspector.showContentLevelError).toHaveBeenCalledWith(
      "kaputt",
    );

    fixture.api.put.mockRejectedValueOnce("unknown");
    await fixture.controller.assign("image-1", "standard");
    expect(fixture.inspector.showContentLevelError).toHaveBeenCalledWith(
      "Die Inhaltsstufe konnte nicht geändert werden.",
    );

    const errorCallsBeforeAbort =
      fixture.inspector.showContentLevelError.mock.calls.length;
    fixture.api.put.mockRejectedValueOnce(
      new DOMException("aborted", "AbortError"),
    );
    await fixture.controller.assign("image-1", "nude");
    expect(fixture.inspector.showContentLevelError).toHaveBeenCalledTimes(
      errorCallsBeforeAbort + 1,
    );
  });

  it("uses confirmation and the canonical image delete endpoint", async () => {
    const fixture = createFixture();
    fixture.dialog.confirm.mockResolvedValueOnce(false);
    await fixture.controller.delete("image-1");
    expect(fixture.api.post).not.toHaveBeenCalled();

    fixture.dialog.confirm.mockResolvedValueOnce(true);
    await fixture.controller.delete("image/1");
    expect(fixture.api.post).toHaveBeenCalledWith(
      "images/image%2F1/delete",
      {},
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(fixture.onDeleted).toHaveBeenCalledOnce();

    fixture.dialog.confirm.mockResolvedValueOnce(true);
    fixture.api.post.mockRejectedValueOnce(new Error("Löschen fehlgeschlagen"));
    await fixture.controller.delete("image-2");
    expect(fixture.inspector.showContentLevelError).toHaveBeenCalledWith(
      "Löschen fehlgeschlagen",
    );

    fixture.dialog.confirm.mockResolvedValueOnce(true);
    fixture.api.post.mockRejectedValueOnce(
      new DOMException("aborted", "AbortError"),
    );
    await fixture.controller.delete("image-3");

    const pending = deferred();
    fixture.dialog.confirm.mockResolvedValue(true);
    fixture.api.post.mockReturnValueOnce(pending.promise);
    const first = fixture.controller.delete("image-4");
    await Promise.resolve();
    await fixture.controller.delete("image-5");
    pending.resolve({});
    await first;

    fixture.controller.dispose();
    expect(fixture.requests.dispose).toHaveBeenCalledOnce();
    expect(fixture.dialog.dispose).toHaveBeenCalledOnce();
  });
});

function createFixture() {
  const api = {
    put: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
  };
  const inspector = {
    setContentLevelBusy: vi.fn(),
    showContentLevelError: vi.fn(),
  };
  const requests = {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    dispose: vi.fn(),
  };
  const dialog = {
    confirm: vi.fn().mockResolvedValue(true),
    dispose: vi.fn(),
  };
  const onChanged = vi.fn().mockResolvedValue(undefined);
  const onDeleted = vi.fn().mockResolvedValue(undefined);
  return {
    controller: new ImageContentLevelController({
      api,
      inspector,
      requests,
      dialog,
      onChanged,
      onDeleted,
    }),
    api,
    inspector,
    requests,
    dialog,
    onChanged,
    onDeleted,
  };
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
