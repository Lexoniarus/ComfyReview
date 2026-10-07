import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { CatalogController } from "../../static/js/surfaces/catalog-controller.js";

describe("CatalogController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads, selects, creates, updates, archives and disposes", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    expect(fixture.browser.render).toHaveBeenCalledWith([
      { component_uid: "component-a" },
      expect.objectContaining({
        component_uid: "lora-a",
        catalog_kind: "lora",
        name: "Style",
      }),
    ]);

    await fixture.controller.select("component-a");
    expect(fixture.editor.render).toHaveBeenCalledWith(
      expect.objectContaining({ component_uid: "component-a" }),
      [{ revision_number: 1 }],
    );

    await fixture.controller.save({ name: "Updated" });
    expect(fixture.api.put).toHaveBeenCalledWith(
      "catalog/components/component-a",
      { name: "Updated" },
      expect.any(Object),
    );

    fixture.controller.create();
    expect(fixture.editor.create).toHaveBeenCalledOnce();
    await fixture.controller.save({ name: "New" });
    expect(fixture.api.post).toHaveBeenCalledWith(
      "catalog/components",
      { name: "New" },
      expect.any(Object),
    );

    await fixture.controller.setArchived(true);
    expect(fixture.api.patch).toHaveBeenCalledWith(
      "catalog/components/component-a",
      { archived: true },
      expect.any(Object),
    );
    expect(fixture.status.textContent).toBe("Katalogeintrag archiviert");
    await fixture.controller.setArchived(false);
    expect(fixture.status.textContent).toBe("Katalogeintrag wiederhergestellt");

    fixture.controller.dispose();
    expect(fixture.browser.dispose).toHaveBeenCalledOnce();
    expect(fixture.editor.dispose).toHaveBeenCalledOnce();
  });

  it("binds the new action and surfaces read and mutation failures", async () => {
    const loadFailure = createFixture({ loadError: "unknown" });
    await loadFailure.controller.start();
    expect(loadFailure.status.textContent).toBe(
      "Die Anfrage ist fehlgeschlagen.",
    );

    const selectFailure = createFixture({
      selectError: new Error("lesen kaputt"),
    });
    await selectFailure.controller.start();
    await selectFailure.controller.select("component-a");
    expect(selectFailure.status.textContent).toBe("lesen kaputt");

    const mutationFailure = createFixture({
      mutationError: new Error("schreiben kaputt"),
    });
    await mutationFailure.controller.start();
    await mutationFailure.controller.save({});
    expect(mutationFailure.status.textContent).toBe("schreiben kaputt");
    await mutationFailure.controller.select("component-a");
    await mutationFailure.controller.setArchived(true);
    expect(mutationFailure.status.textContent).toBe("schreiben kaputt");

    const idle = createFixture();
    await idle.controller.start();
    await idle.controller.setArchived(true);
    expect(idle.api.patch).not.toHaveBeenCalled();
    idle.newButton.click();
    expect(idle.editor.create).toHaveBeenCalledOnce();
  });
});

function createFixture(options = {}) {
  const newButton = document.createElement("button");
  const status = document.createElement("p");
  const browser = disposable({ render: vi.fn(), select: vi.fn() });
  const editor = disposable({
    create: vi.fn(),
    render: vi.fn(),
    setBusy: vi.fn(),
  });
  const api = {
    get: vi.fn((path) => {
      if (options.loadError && path.includes("include_archived")) {
        return Promise.reject(options.loadError);
      }
      if (options.selectError && !path.includes("include_archived")) {
        return Promise.reject(options.selectError);
      }
      if (path.includes("revisions")) {
        return Promise.resolve({ revisions: [{ revision_number: 1 }] });
      }
      if (path.includes("include_archived")) {
        if (path.includes("catalog/loras")) {
          return Promise.resolve({
            loras: [
              {
                lora_uid: "lora-a",
                provider_name: "style.safetensors",
                display_name: "Style",
              },
            ],
          });
        }
        return Promise.resolve({
          components: [{ component_uid: "component-a" }],
        });
      }
      return Promise.resolve({ component_uid: "component-a" });
    }),
    post: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve({ component_uid: "component-a" }),
    ),
    put: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve({ component_uid: "component-a" }),
    ),
    patch: vi.fn(() =>
      options.mutationError
        ? Promise.reject(options.mutationError)
        : Promise.resolve({ component_uid: "component-a" }),
    ),
  };
  return {
    controller: new CatalogController({
      api,
      browser,
      editor,
      requests: new RequestLifecycle(),
      newButton,
      status,
    }),
    api,
    browser,
    editor,
    newButton,
    status,
  };
}

function disposable(methods) {
  return { ...methods, dispose: vi.fn() };
}
