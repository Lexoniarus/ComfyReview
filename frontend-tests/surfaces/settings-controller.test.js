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
      "profiles",
      fixture.data,
    );
    expect(
      fixture.navigation.querySelector("button").getAttribute("aria-current"),
    ).toBe("true");

    await fixture.controller.savePreferences({ density: "compact" });
    await fixture.controller.saveProfile(null, { name: "New" });
    await fixture.controller.saveProfile("profile-a", { name: "Updated" });
    await fixture.controller.archiveProfile("profile-a", true);
    await fixture.controller.defaultProfile("profile-a");
    await fixture.controller.checkComfyUi();

    expect(fixture.api.put).toHaveBeenCalledWith("settings/preferences", {
      density: "compact",
    });
    expect(fixture.api.post).toHaveBeenCalledWith(
      "settings/generation-profiles",
      {
        name: "New",
      },
    );
    expect(fixture.api.put).toHaveBeenCalledWith(
      "settings/generation-profiles/profile-a",
      { name: "Updated" },
    );
    expect(fixture.api.patch).toHaveBeenCalledWith(
      "settings/generation-profiles/profile-a/archive",
      { archived: true },
    );
    expect(fixture.api.put).toHaveBeenCalledWith(
      "settings/generation-profiles/profile-a/default",
      {},
    );
    expect(fixture.api.post).toHaveBeenCalledWith("settings/comfyui/check", {});
    expect(fixture.status.textContent).toBe("Gespeichert.");

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
      "Speichern fehlgeschlagen.",
    );
  });
});

function createFixture(options = {}) {
  const data = { preferences: { density: "comfortable" } };
  const api = {
    get: vi.fn(() =>
      options.loadError
        ? Promise.reject(options.loadError)
        : Promise.resolve(data),
    ),
    put: vi.fn(() => mutation(options)),
    post: vi.fn(() => mutation(options)),
    patch: vi.fn(() => mutation(options)),
  };
  const navigation = document.createElement("nav");
  const button = document.createElement("button");
  button.dataset.section = "profiles";
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
