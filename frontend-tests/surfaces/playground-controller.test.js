import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { PlaygroundController } from "../../static/js/surfaces/playground-controller.js";

describe("PlaygroundController", () => {
  beforeEach(() => document.body.replaceChildren());

  it("loads canonical inputs, prepares a draft, submits it, and disposes", async () => {
    const fixture = createFixture();
    await fixture.controller.start();
    expect(fixture.modes.render).toHaveBeenCalledWith(
      [{ component_uid: "a" }],
      [],
    );
    expect(fixture.controls.render).toHaveBeenCalled();
    expect(fixture.controls.render).toHaveBeenCalledWith({ defaults: {} });
    expect(fixture.modes.applyState).toHaveBeenCalledWith({});
    expect(fixture.controls.applyState).toHaveBeenCalledWith({});
    expect(fixture.modes.applyIntent).toHaveBeenCalledWith({});
    expect(fixture.controls.applyIntent).toHaveBeenCalledWith({});

    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      { selections: [], generation: expect.any(Object) },
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
    expect(
      empty.api.post.mock.calls.some(([path]) => path === "generations"),
    ).toBe(false);

    const previewFailure = createFixture({
      previewError: new Error("preview kaputt"),
    });
    await previewFailure.controller.refreshPreview();
    expect(previewFailure.status.textContent).toBe("preview kaputt");

    const noPreview = createFixture({ emptyPromptPayload: true });
    await noPreview.controller.refreshPreview();
    await noPreview.controller.refreshEvidence();
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

  it("prefills visible component selections from an image handoff", async () => {
    const fixture = createFixture({
      intent: { imageUid: "image-1" },
      image: {
        image_uid: "image-1",
        prompt_setup: {
          source_image_uid: "image-1",
          component_uids: ["character-a"],
          revision_uids: ["revision-character-a"],
          loras: [],
        },
        render_setup: {
          checkpoint: "model.safetensors",
          seed: 42,
          aspect_format: "1:1",
          resolution_class: "1080",
          sampler_stages: [
            {
              sampler: "euler",
              scheduler: "normal",
              steps: 24,
              cfg: 6.5,
              denoise: 1,
            },
          ],
        },
      },
    });

    await fixture.controller.start();
    expect(fixture.api.get).toHaveBeenCalledWith(
      "images/image-1/generator-handoff",
      expect.any(Object),
    );
    expect(fixture.modes.applyIntent).toHaveBeenCalledWith(
      expect.objectContaining({
        componentUids: ["character-a"],
      }),
    );
    expect(
      fixture.api.post.mock.calls.some(
        ([path]) => path === "playground/drafts",
      ),
    ).toBe(false);
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      {
        selections: [],
        generation: expect.any(Object),
      },
      expect.any(Object),
    );
    fixture.controller.clearDraftReference();
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      { selections: [], generation: expect.any(Object) },
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
    expect(
      fixture.api.post.mock.calls.some(
        ([path]) => path === "playground/drafts",
      ),
    ).toBe(false);
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      {
        composition_uid: "composition-a",
        generation: expect.any(Object),
      },
      expect.any(Object),
    );
  });

  it("keeps rejected image staging and resolves independent packages", async () => {
    const intentStore = { clear: vi.fn() };
    const fixture = createFixture({
      intent: {
        promptImageUid: "image-prompt",
        renderImageUid: "image-render",
      },
      intentRejected: ["checkpoint"],
      intentStore,
      image: {
        prompt_setup: {
          source_image_uid: "image-prompt",
          component_uids: ["character-a"],
          revision_uids: ["revision-character-a"],
          loras: [],
        },
        render_setup: {
          checkpoint: "missing.safetensors",
          seed: 42,
          aspect_format: "1:1",
          resolution_class: "1080",
          sampler_stages: [
            {
              sampler: "euler",
              scheduler: "normal",
              steps: 24,
              cfg: 6.5,
              denoise: 1,
            },
          ],
        },
      },
    });

    await fixture.controller.start();

    expect(
      fixture.api.get.mock.calls.filter(([path]) => path.startsWith("images/")),
    ).toHaveLength(2);
    expect(fixture.status.textContent).toContain("checkpoint");
    expect(intentStore.clear).not.toHaveBeenCalled();
  });

  it("keeps revision-only prompt provenance for explicit draft creation", async () => {
    const fixture = createFixture({
      intent: { revisionUids: ["revision-character-a"] },
    });
    await fixture.controller.start();
    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      {
        revision_uids: ["revision-character-a"],
        generation: expect.any(Object),
      },
      expect.any(Object),
    );
  });

  it("owns guidance modes, explicit application, invalidation and refresh errors", async () => {
    vi.useFakeTimers();
    try {
      const fixture = createFixture({ rejected: ["checkpoint"] });
      fixture.controller.guidanceModeChanged("predicted");
      await fixture.controller.start();
      fixture.controller.guidanceModeChanged("predicted");
      expect(fixture.controls.renderGuidance).toHaveBeenLastCalledWith(
        expect.any(Object),
        "predicted",
      );
      fixture.submitButton.disabled = false;
      fixture.controller.settingsChanged();
      expect(fixture.submitButton.disabled).toBe(true);
      await vi.advanceTimersByTimeAsync(180);
      expect(fixture.api.post).toHaveBeenCalledWith(
        "playground/render-guidance",
        expect.any(Object),
        expect.any(Object),
      );
      fixture.controller.applyGuidanceSetup({ checkpoint: "missing" });
      expect(fixture.status.textContent).toContain("checkpoint");
      fixture.controller.applyGuidanceParameter("custom", "x");
      expect(fixture.status.textContent).toContain("custom übernommen");
      fixture.controller.dispose();

      const unavailable = createFixture({ parameterAvailable: false });
      unavailable.controller.applyGuidanceSetup({ sampler: "euler" });
      expect(unavailable.status.textContent).toContain(
        "Gesamtsetup übernommen",
      );
      unavailable.controller.applyGuidanceParameter("sampler", "missing");
      expect(unavailable.status.textContent).toContain("nicht verfügbar");

      const failed = createFixture({
        guidanceError: new Error("guidance kaputt"),
      });
      await failed.controller.refreshGuidance();
      expect(failed.guidance.renderLoading).toHaveBeenLastCalledWith(
        "guidance kaputt",
      );
      const aborted = createFixture({
        guidanceError: new DOMException("aborted", "AbortError"),
      });
      await aborted.controller.refreshGuidance();
      expect(aborted.guidance.renderLoading).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("restores saved values and persists the complete state after changes", async () => {
    vi.useFakeTimers();
    try {
      const savedState = { checkpoint: "saved.safetensors" };
      const fixture = createFixture({ savedState });

      await fixture.controller.start();
      expect(fixture.modes.applyState).toHaveBeenCalledWith(savedState);
      expect(fixture.controls.applyState).toHaveBeenCalledWith(savedState);

      fixture.controller.settingsChanged();
      fixture.controller.settingsChanged();
      await vi.advanceTimersByTimeAsync(180);
      await settle();

      expect(fixture.api.put).toHaveBeenCalledOnce();
      expect(fixture.api.put).toHaveBeenCalledWith(
        "playground/generator-state",
        {
          selections: [],
          checkpoint: "model",
          seed_mode: "fixed",
        },
        expect.any(Object),
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("carries an exact fixed revision through state save and draft preparation", async () => {
    vi.useFakeTimers();
    try {
      const selection = {
        kind: "character",
        mode: "fixed",
        component_uid: "character-a",
        revision_uid: "character-rev-1",
      };
      const savedState = { selections: [selection] };
      const fixture = createFixture({
        savedState,
        selectionValue: { selections: [selection] },
      });

      await fixture.controller.start();
      expect(fixture.modes.applyState).toHaveBeenCalledWith(savedState);
      await fixture.controller.prepare();
      expect(fixture.api.post).toHaveBeenCalledWith(
        "playground/drafts",
        {
          selections: [selection],
          generation: expect.any(Object),
        },
        expect.any(Object),
      );

      fixture.controller.settingsChanged();
      await vi.advanceTimersByTimeAsync(180);
      await settle();
      expect(fixture.api.put).toHaveBeenCalledWith(
        "playground/generator-state",
        {
          selections: [selection],
          checkpoint: "model",
          seed_mode: "fixed",
        },
        expect.any(Object),
      );
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the generator usable when state loading or saving fails", async () => {
    vi.useFakeTimers();
    try {
      const fixture = createFixture({
        stateLoadError: new Error("state load kaputt"),
        stateSaveError: new Error("state save kaputt"),
      });

      await fixture.controller.start();
      expect(fixture.prepareButton.disabled).toBe(false);
      fixture.controller.clearDraftReference();
      await vi.advanceTimersByTimeAsync(180);
      await settle();

      expect(fixture.status.textContent).toContain(
        "Einstellungen konnten nicht gespeichert werden",
      );
    } finally {
      vi.useRealTimers();
    }
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
    applyState: vi.fn(() => options.stateRejected || []),
    applyIntent: vi.fn(() => options.intentRejected || []),
    showResolvedComponents: vi.fn(),
    value: vi.fn(() => options.selectionValue || { selections: [] }),
  });
  const controls = disposable({
    render: vi.fn(),
    applyState: vi.fn(() => options.stateRejected || []),
    applyIntent: vi.fn(() => options.intentRejected || []),
    stateValue: vi.fn(() => ({
      checkpoint: "model",
      seed_mode: "fixed",
    })),
    renderSettings: vi.fn(() => ({
      checkpoint: "model",
      sampler: "euler",
      scheduler: "normal",
      steps: 24,
      cfg: 6.5,
      denoise: 1,
    })),
    renderGuidance: vi.fn(),
    applyRenderSettings: vi.fn(() => options.rejected || []),
    applyParameter: vi.fn(() => options.parameterAvailable !== false),
    draftValue: vi.fn(() => ({
      checkpoint: "model",
      sampler: "euler",
      scheduler: "normal",
      seed: 17,
      randomize_seed: false,
      steps: 24,
      cfg: 6.5,
      denoise: 1,
      aspect_format: "1:1",
      resolution_class: "1080",
    })),
    value: vi.fn(() => ({ checkpoint: "model", sampler: {} })),
    useConcreteSeed: vi.fn(),
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
    renderEvidence: vi.fn(),
    generationPayload: vi.fn(() =>
      options.emptyPayload ? null : { draft_uid: "draft-1" },
    ),
  });
  const api = {
    get: vi.fn((path) => {
      if (options.loadError) return Promise.reject(options.loadError);
      if (path === "playground/generator-state")
        return options.stateLoadError
          ? Promise.reject(options.stateLoadError)
          : Promise.resolve(options.savedState || {});
      return Promise.resolve(
        path.startsWith("images/")
          ? options.image
          : path === "playground/components"
            ? { components: [{ component_uid: "a" }] }
            : { defaults: {} },
      );
    }),
    put: vi.fn(() =>
      options.stateSaveError
        ? Promise.reject(options.stateSaveError)
        : Promise.resolve({}),
    ),
    post: vi.fn((path) => {
      if (path === "playground/render-guidance") {
        return options.guidanceError
          ? Promise.reject(options.guidanceError)
          : Promise.resolve({ recommendations: {}, parameter_values: [] });
      }
      if (path === "playground/drafts") {
        return options.draftError
          ? Promise.reject(options.draftError)
          : Promise.resolve({
              draft_uid: "draft-1",
              seed: 17,
              positive_prompt: "positive",
            });
      }
      if (path === "playground/render-preview") {
        return options.previewError
          ? Promise.reject(options.previewError)
          : Promise.resolve({
              positive_prompt: "preview positive",
              negative_prompt: "preview negative",
            });
      }
      if (path === "playground/evidence") {
        return Promise.resolve({ prompt_match: null, sampler_match: null });
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
  const guidance = disposable({
    render: vi.fn(),
    renderLoading: vi.fn(),
  });
  const controller = new PlaygroundController({
    api,
    modes,
    controls,
    draft,
    guidance,
    requests: new RequestLifecycle(),
    previewRequests: new RequestLifecycle(),
    guidanceRequests: new RequestLifecycle(),
    stateRequests: new RequestLifecycle(),
    prepareButton,
    submitButton,
    status,
    result,
    intent: options.intent,
    intentStore: options.intentStore,
  });
  return {
    controller,
    api,
    modes,
    controls,
    draft,
    prepareButton,
    submitButton,
    status,
    result,
    guidance,
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
