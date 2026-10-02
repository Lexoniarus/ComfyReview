import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { PlaygroundController } from "../../static/js/surfaces/playground-controller.js";

describe("PlaygroundController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads canonical inputs, prepares a draft, submits it, and disposes", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    expect(fixture.modes.render).toHaveBeenCalledWith([{ component_uid: "a" }]);
    expect(fixture.controls.render).toHaveBeenCalled();
    expect(fixture.combinations.render).toHaveBeenCalledWith({
      two_component: [],
    });

    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      { selections: [], seed: 17 },
      expect.any(Object),
    );
    expect(fixture.draft.render).toHaveBeenCalledWith(
      expect.objectContaining({ positive_prompt: "positive" }),
      "draft-1",
    );

    await fixture.controller.submit();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "generations",
      expect.objectContaining({ draft_uid: "draft-1" }),
      expect.any(Object),
    );
    expect(fixture.result.dataset.state).toBe("success");
    expect(fixture.result.textContent).toContain("generation-1");

    fixture.controller.dispose();
    expect(fixture.modes.dispose).toHaveBeenCalledOnce();
    expect(fixture.controls.dispose).toHaveBeenCalledOnce();
    expect(fixture.draft.dispose).toHaveBeenCalledOnce();
    expect(fixture.combinations.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces load, draft and generation failures without stale submits", async () => {
    const loading = createFixture({ loadError: "unknown" });
    await loading.controller.start();
    expect(loading.status.textContent).toBe("Die Anfrage ist fehlgeschlagen.");
    expect(loading.prepareButton.disabled).toBe(true);

    const draftFailure = createFixture({
      draftError: new Error("draft kaputt"),
    });
    await draftFailure.controller.start();
    await draftFailure.controller.prepare();
    expect(draftFailure.status.textContent).toBe("draft kaputt");
    expect(draftFailure.submitButton.disabled).toBe(true);

    const generationFailure = createFixture({
      generationError: new Error("comfy kaputt"),
    });
    await generationFailure.controller.start();
    await generationFailure.controller.submit();
    expect(generationFailure.result.dataset.state).toBe("error");
    expect(generationFailure.result.textContent).toBe("comfy kaputt");

    const empty = createFixture({ emptyPayload: true });
    await empty.controller.start();
    await empty.controller.submit();
    expect(empty.api.post).not.toHaveBeenCalled();
  });

  it("binds its action buttons through one owned listener lifecycle", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    fixture.prepareButton.click();
    await settle();
    expect(fixture.draft.render).toHaveBeenCalled();
    fixture.submitButton.disabled = false;
    fixture.submitButton.click();
    await settle();
    expect(fixture.result.dataset.state).toBe("success");
  });

  it("reports every generation returned for a batch", async () => {
    const fixture = createFixture({ batch: true });
    await fixture.controller.start();
    await fixture.controller.submit();

    expect(fixture.result.textContent).toContain("generation-2 · submitted");
    expect(fixture.status.textContent).toBe(
      "2 Generierungen an ComfyUI übergeben",
    );
  });
});

function createFixture(options = {}) {
  const prepareButton = document.createElement("button");
  const submitButton = document.createElement("button");
  submitButton.disabled = true;
  const status = document.createElement("span");
  const result = document.createElement("div");
  const modes = disposable({
    render: vi.fn(),
    value: vi.fn(() => ({ selections: [], seed: 17 })),
  });
  const controls = disposable({
    render: vi.fn(),
    value: vi.fn(() => ({ checkpoint: "model", sampler: {} })),
    setBusy: vi.fn(),
  });
  const draft = disposable({
    render: vi.fn(),
    generationPayload: vi.fn(() =>
      options.emptyPayload ? null : { draft_uid: "draft-1" },
    ),
  });
  const combinations = disposable({ render: vi.fn() });
  const api = {
    get: vi.fn((path) => {
      if (options.loadError) return Promise.reject(options.loadError);
      return Promise.resolve(
        path === "catalog/components"
          ? { components: [{ component_uid: "a" }] }
          : path === "playground/top-combinations"
            ? { two_component: [] }
            : { defaults: {} },
      );
    }),
    post: vi.fn((path) => {
      if (path === "playground/drafts") {
        return options.draftError
          ? Promise.reject(options.draftError)
          : Promise.resolve({ positive_prompt: "positive" });
      }
      return options.generationError
        ? Promise.reject(options.generationError)
        : Promise.resolve({
            generation_uid: "generation-1",
            status: "submitted",
            submissions: options.batch
              ? [
                  { generation_uid: "generation-1", status: "submitted" },
                  { generation_uid: "generation-2", status: "submitted" },
                ]
              : undefined,
          });
    }),
  };
  const controller = new PlaygroundController({
    api,
    modes,
    controls,
    draft,
    combinations,
    requests: new RequestLifecycle(),
    prepareButton,
    submitButton,
    status,
    result,
    newDraftUid: () => "draft-1",
  });
  return {
    controller,
    api,
    modes,
    controls,
    draft,
    combinations,
    prepareButton,
    submitButton,
    status,
    result,
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
