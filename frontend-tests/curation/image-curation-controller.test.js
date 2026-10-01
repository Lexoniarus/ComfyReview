import { describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { ImageCurationController } from "../../static/js/curation/image-curation-controller.js";

describe("ImageCurationController", () => {
  it("loads canonical set choices and refreshes after a UID-only assignment", async () => {
    const fixture = createFixture();

    await fixture.controller.start();
    await fixture.controller.assign("image/1", "outfit");

    expect(fixture.api.get).toHaveBeenCalledWith(
      "curation/sets",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(fixture.inspector.setCurationOptions).toHaveBeenCalledWith([
      "character_face",
      "outfit",
    ]);
    expect(fixture.api.put).toHaveBeenCalledWith(
      "images/image%2F1/curation",
      { set_key: "outfit" },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(fixture.onAssigned).toHaveBeenCalledWith("image/1");
    expect(fixture.inspector.setCurationBusy).toHaveBeenNthCalledWith(1, true);
    expect(fixture.inspector.setCurationBusy).toHaveBeenLastCalledWith(false);

    const empty = createFixture({ emptySets: true });
    await empty.controller.start();
    expect(empty.inspector.setCurationOptions).toHaveBeenCalledWith([]);
  });

  it("surfaces read and mutation failures while ignoring aborted work", async () => {
    const readFailure = createFixture({ readError: new Error("sets kaputt") });
    await readFailure.controller.start();
    expect(readFailure.inspector.showCurationError).toHaveBeenCalledWith(
      "sets kaputt",
    );

    const mutationFailure = createFixture({ mutationError: "unknown" });
    await mutationFailure.controller.assign("image-1", "pose");
    expect(mutationFailure.inspector.showCurationError).toHaveBeenCalledWith(
      "Die Anfrage ist fehlgeschlagen.",
    );

    const aborted = createFixture({
      mutationError: new DOMException("aborted", "AbortError"),
    });
    await aborted.controller.assign("image-1", "pose");
    expect(aborted.inspector.showCurationError).toHaveBeenCalledOnce();
    expect(aborted.inspector.showCurationError).toHaveBeenCalledWith("");

    const abortedRead = createFixture({
      readError: new DOMException("aborted", "AbortError"),
    });
    await abortedRead.controller.start();
    expect(abortedRead.inspector.showCurationError).not.toHaveBeenCalled();
  });

  it("blocks duplicate assignments and disposes its request owner", async () => {
    let resolveMutation = () => {};
    const mutation = new Promise((resolve) => {
      resolveMutation = resolve;
    });
    const fixture = createFixture({ mutation });

    const first = fixture.controller.assign("image-1", "pose");
    await fixture.controller.assign("image-2", "outfit");
    expect(fixture.api.put).toHaveBeenCalledOnce();
    resolveMutation({});
    await first;
    fixture.controller.dispose();
    fixture.controller.dispose();

    await fixture.controller.start();
    expect(fixture.api.get).not.toHaveBeenCalled();
  });
});

function createFixture(options = {}) {
  const api = {
    get: vi.fn(() =>
      options.readError
        ? Promise.reject(options.readError)
        : Promise.resolve(
            options.emptySets ? {} : { set_keys: ["character_face", "outfit"] },
          ),
    ),
    put: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : options.mutation || Promise.resolve({}),
    ),
  };
  const inspector = {
    setCurationOptions: vi.fn(),
    setCurationBusy: vi.fn(),
    showCurationError: vi.fn(),
  };
  const onAssigned = vi.fn(() => Promise.resolve());
  const controller = new ImageCurationController({
    api,
    inspector,
    requests: new RequestLifecycle(),
    onAssigned,
  });
  return { controller, api, inspector, onAssigned };
}
