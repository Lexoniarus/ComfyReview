import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { SettingsController } from "../../static/js/surfaces/settings-controller.js";

describe("SettingsController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads, navigates, mutates every settings resource and disposes", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    expect(fixture.view.render).toHaveBeenCalledWith("general", fixture.data);

    fixture.navigation.querySelector("button").click();
    expect(fixture.view.render).toHaveBeenLastCalledWith(
      "content",
      fixture.data,
    );
    expect(
      fixture.navigation.querySelector("button").getAttribute("aria-current"),
    ).toBe("true");

    await fixture.controller.savePreferences({ density: "compact" });
    await fixture.controller.classifyLora("style.safetensors", "lewd");
    await fixture.controller.previewLora("lora/style");
    await fixture.controller.reclassifyLora("lora/style", 3);
    await fixture.controller.checkComfyUi();

    expect(fixture.api.put).toHaveBeenCalledWith("settings/preferences", {
      density: "compact",
    });
    expect(fixture.api.post).toHaveBeenCalledWith("settings/comfyui/check", {});
    expect(fixture.api.post).toHaveBeenCalledWith("settings/loras/classify", {
      provider_name: "style.safetensors",
      content_level: "lewd",
    });
    expect(fixture.api.get).toHaveBeenCalledWith(
      "settings/loras/lora%2Fstyle/reclassification-impact",
    );
    expect(fixture.api.post).toHaveBeenCalledWith(
      "settings/loras/lora%2Fstyle/reclassify",
      { expected_revision: 3 },
    );
    expect(fixture.view.render).toHaveBeenLastCalledWith(
      "comfyui",
      expect.objectContaining({ runtime: { connected: true } }),
    );
    expect(fixture.status.textContent).toBe("Verbunden.");

    fixture.controller.dispose();
    expect(fixture.view.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces loading and mutation failures while ignoring cancellation", async () => {
    const loadFailure = createFixture({ loadError: new Error("offline") });
    await loadFailure.controller.start();
    expect(loadFailure.status.textContent).toBe("offline");

    const unknownFailure = createFixture({ loadError: "invalid" });
    await unknownFailure.controller.start();
    expect(unknownFailure.status.textContent).toContain("nicht geladen");

    const cancelled = createFixture({
      loadError: new DOMException("cancelled", "AbortError"),
    });
    await cancelled.controller.start();
    expect(cancelled.status.textContent).toContain("werden geladen");

    const mutationFailure = createFixture({
      mutationError: new Error("kaputt"),
    });
    await mutationFailure.controller.start();
    await mutationFailure.controller.savePreferences({});
    expect(mutationFailure.status.textContent).toBe("kaputt");

    const unknownMutation = createFixture({ mutationError: "invalid" });
    await unknownMutation.controller.start();
    await unknownMutation.controller.checkComfyUi();
    expect(unknownMutation.status.textContent).toBe(
      "Verbindungstest fehlgeschlagen.",
    );

    const previewFailure = createFixture({
      previewError: new Error("Vorschau kaputt"),
    });
    await previewFailure.controller.start();
    await previewFailure.controller.previewLora("lora-a");
    expect(previewFailure.status.textContent).toBe("Vorschau kaputt");
  });
});

function createFixture(options = {}) {
  const data = { preferences: { density: "comfortable" } };
  const api = {
    get: vi.fn((path) => {
      if (path.includes("reclassification-impact")) {
        return options.previewError
          ? Promise.reject(options.previewError)
          : Promise.resolve({ revision: 3, image_count: 2 });
      }
      return options.loadError
        ? Promise.reject(options.loadError)
        : Promise.resolve(data);
    }),
    put: vi.fn(() => mutation(options)),
    post: vi.fn((path) =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve(
            path === "settings/comfyui/check"
              ? { connected: true }
              : { ok: true },
          ),
    ),
    patch: vi.fn(() => mutation(options)),
  };
  const navigation = document.createElement("nav");
  const button = document.createElement("button");
  button.dataset.section = "content";
  navigation.append(button);
  const status = document.createElement("p");
  const view = { render: vi.fn(), dispose: vi.fn() };
  return {
    controller: new SettingsController({
      api,
      requests: new RequestLifecycle(),
      view,
      navigation,
      status,
    }),
    api,
    data,
    navigation,
    status,
    view,
  };
}

function mutation(options) {
  return options.mutationError
    ? Promise.reject(options.mutationError)
    : Promise.resolve({ ok: true });
}
