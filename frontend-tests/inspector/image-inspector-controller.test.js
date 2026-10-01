import { describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { ImageInspectorController } from "../../static/js/inspector/image-inspector-controller.js";

describe("ImageInspectorController", () => {
  it("loads canonical review history for the current image", async () => {
    const api = {
      get: vi.fn().mockResolvedValue({ events: [{ event_uid: "event-1" }] }),
    };
    const view = inspectorView();
    const controller = new ImageInspectorController({
      api,
      view,
      requests: new RequestLifecycle(),
    });

    controller.render({ image_uid: "image/a" });

    expect(view.render).toHaveBeenCalledWith({ image_uid: "image/a" });
    expect(view.reviewsLoading).toHaveBeenCalledOnce();
    await vi.waitFor(() => {
      expect(view.renderReviews).toHaveBeenCalledWith([
        { event_uid: "event-1" },
      ]);
    });
    expect(api.get).toHaveBeenCalledWith("images/image%2Fa/reviews", {
      signal: expect.any(AbortSignal),
    });
    controller.dispose();
    expect(view.dispose).toHaveBeenCalledOnce();
  });

  it("owns status delegation and ignores stale history", async () => {
    let resolveHistory = () => {};
    const history = new Promise((resolve) => {
      resolveHistory = () => resolve({ events: [{ event_uid: "stale" }] });
    });
    const api = { get: vi.fn(() => history) };
    const view = inspectorView();
    const controller = new ImageInspectorController({
      api,
      view,
      requests: new RequestLifecycle(),
    });

    controller.render({ image_uid: "image-1" });
    controller.loading();
    resolveHistory();
    await history;
    await Promise.resolve();
    expect(view.renderReviews).not.toHaveBeenCalled();

    controller.render({});
    expect(api.get).toHaveBeenCalledOnce();
    controller.empty();
    controller.error("Kaputt");
    expect(view.loading).toHaveBeenCalledOnce();
    expect(view.empty).toHaveBeenCalledOnce();
    expect(view.error).toHaveBeenCalledWith("Kaputt");
    controller.dispose();
  });

  it("normalizes history failures and suppresses aborts", async () => {
    const view = inspectorView();
    const api = {
      get: vi
        .fn()
        .mockRejectedValueOnce(new Error("API kaputt"))
        .mockRejectedValueOnce({})
        .mockRejectedValueOnce(new DOMException("aborted", "AbortError"))
        .mockResolvedValueOnce({}),
    };
    const controller = new ImageInspectorController({
      api,
      view,
      requests: new RequestLifecycle(),
    });

    controller.render({ image_uid: "image-1" });
    await vi.waitFor(() => {
      expect(view.reviewsError).toHaveBeenCalledWith("API kaputt");
    });
    controller.render({ image_uid: "image-2" });
    await vi.waitFor(() => {
      expect(view.reviewsError).toHaveBeenCalledWith(
        "Bewertungshistorie konnte nicht geladen werden.",
      );
    });
    controller.render({ image_uid: "image-3" });
    await Promise.resolve();
    expect(view.reviewsError).toHaveBeenCalledTimes(2);
    controller.render({ image_uid: "image-4" });
    await vi.waitFor(() => {
      expect(view.renderReviews).toHaveBeenCalledWith([]);
    });
    controller.dispose();
  });
});

function inspectorView() {
  return {
    render: vi.fn(),
    renderReviews: vi.fn(),
    reviewsLoading: vi.fn(),
    reviewsError: vi.fn(),
    loading: vi.fn(),
    empty: vi.fn(),
    error: vi.fn(),
    dispose: vi.fn(),
  };
}
