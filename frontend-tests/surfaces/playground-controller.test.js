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
    expect(fixture.controls.render).toHaveBeenCalledWith(
      expect.objectContaining({ profiles: [] }),
    );
    expect(fixture.modes.applyIntent).toHaveBeenCalledWith({});
    expect(fixture.controls.applyIntent).toHaveBeenCalledWith({});
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
    await fixture.controller.refreshPreview();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/render-preview",
      expect.objectContaining({ positive_atoms: [] }),
      expect.any(Object),
    );
    expect(fixture.draft.renderSnapshots).toHaveBeenCalledWith({
      positive_prompt: "preview positive",
      negative_prompt: "preview negative",
    });

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

    const previewFailure = createFixture({
      previewError: new Error("preview kaputt"),
    });
    await previewFailure.controller.refreshPreview();
    expect(previewFailure.status.textContent).toBe("preview kaputt");

    const noPreview = createFixture({ emptyPromptPayload: true });
    await noPreview.controller.refreshPreview();
    expect(noPreview.api.post).not.toHaveBeenCalled();
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

  it("prefills an exact image without drafting or submitting", async () => {
    const fixture = createFixture({
      intent: { imageUid: "image-1" },
      image: {
        image_uid: "image-1",
        scopes: [
          {
            component_uid: "character-a",
            revision_uid: "revision-character-a",
          },
        ],
        generation_settings: {
          checkpoint: "model.safetensors",
          sampler: "euler",
          scheduler: "normal",
          seed: 42,
          steps: 24,
          cfg: 6.5,
          denoise: 1,
        },
      },
    });

    await fixture.controller.start();
    expect(fixture.api.get).toHaveBeenCalledWith(
      "images/image-1",
      expect.any(Object),
    );
    expect(fixture.modes.applyIntent).toHaveBeenCalledWith(
      expect.objectContaining({
        componentUids: ["character-a"],
        revisionUids: ["revision-character-a"],
      }),
    );
    expect(fixture.api.post).not.toHaveBeenCalled();
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      { revision_uids: ["revision-character-a"] },
      expect.any(Object),
    );
    fixture.controller.clearDraftReference();
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenLastCalledWith(
      "playground/drafts",
      { selections: [], seed: 17 },
      expect.any(Object),
    );
  });

  it("keeps a composition handoff as an explicit draft action", async () => {
    const fixture = createFixture({
      intent: {
        compositionUid: "composition-a",
        componentUids: ["character-a", "scene-a"],
      },
    });

    await fixture.controller.start();
    expect(fixture.api.post).not.toHaveBeenCalled();
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      { composition_uid: "composition-a" },
      expect.any(Object),
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
    applyIntent: vi.fn(),
    value: vi.fn(() => ({ selections: [], seed: 17 })),
  });
  const controls = disposable({
    render: vi.fn(),
    applyIntent: vi.fn(),
    value: vi.fn(() => ({ checkpoint: "model", sampler: {} })),
    setBusy: vi.fn(),
  });
  const draft = disposable({
    render: vi.fn(),
    promptPayload: vi.fn(() =>
      options.emptyPromptPayload
        ? null
        : { positive_atoms: [], negative_atoms: [] },
    ),
    renderSnapshots: vi.fn(),
    generationPayload: vi.fn(() =>
      options.emptyPayload ? null : { draft_uid: "draft-1" },
    ),
  });
  const combinations = disposable({ render: vi.fn() });
  const api = {
    get: vi.fn((path) => {
      if (options.loadError) return Promise.reject(options.loadError);
      return Promise.resolve(
        path.startsWith("images/")
          ? options.image
          : path === "playground/components"
            ? { components: [{ component_uid: "a" }] }
            : path === "playground/top-combinations"
              ? { two_component: [] }
              : path === "settings/generation-profiles"
                ? { items: [] }
                : { defaults: {} },
      );
    }),
    post: vi.fn((path) => {
      if (path === "playground/drafts") {
        return options.draftError
          ? Promise.reject(options.draftError)
          : Promise.resolve({ positive_prompt: "positive" });
      }
      if (path === "playground/render-preview") {
        return options.previewError
          ? Promise.reject(options.previewError)
          : Promise.resolve({
              positive_prompt: "preview positive",
              negative_prompt: "preview negative",
            });
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
    previewRequests: new RequestLifecycle(),
    prepareButton,
    submitButton,
    status,
    result,
    newDraftUid: () => "draft-1",
    intent: options.intent,
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
