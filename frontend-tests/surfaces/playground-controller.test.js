import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { PlaygroundIntentStore } from "../../static/js/playground/playground-intent.js";
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

  it("applies typed image prompt selections and LoRAs, persists, and clears only prompt staging", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    intentStore.stageRenderSetup("image-render");
    const promptSelectionState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-a",
          revision_uid: "character-rev-1",
        },
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: "scene-rev-3",
        },
        {
          kind: "outfit",
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
        {
          kind: "pose",
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
        {
          kind: "expression",
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
        {
          kind: "lighting",
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
        {
          kind: "modifier",
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
      ],
      loras: [
        {
          lora_uid: "lora-style",
          revision_uid: "lora-rev-2",
          provider_name: "style.safetensors",
          model_strength: 0.7,
          clip_strength: 0,
        },
      ],
    };
    const handoffLoras = [
      {
        lora_uid: "lora-style",
        revision_uid: "lora-rev-2",
        provider_name: "style.safetensors",
        model_strength: 0.7,
        clip_strength: 0.8,
        model_effective: true,
        clip_effective: false,
      },
      {
        lora_uid: "lora-unused",
        revision_uid: "lora-rev-unused",
        provider_name: "unused.safetensors",
        model_strength: 0.9,
        clip_strength: 0.6,
        model_effective: false,
        clip_effective: false,
      },
    ];
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      savedState: {
        selections: [
          {
            kind: "modifier",
            mode: "fixed",
            component_uid: "modifier-old",
            revision_uid: "modifier-old-rev",
          },
        ],
        loras: [],
      },
      images: {
        "image-prompt": {
          prompt_setup: {
            selections: [
              {
                kind: "scene",
                component_uid: "scene-a",
                revision_uid: "scene-rev-3",
                position: 0,
              },
              {
                kind: "character",
                component_uid: "character-a",
                revision_uid: "character-rev-1",
                position: 0,
              },
            ],
            loras: handoffLoras,
          },
          render_setup: {},
        },
        "image-render": {
          prompt_setup: { selections: [], loras: [] },
          render_setup: {
            applicable: true,
            checkpoint: "handoff.safetensors",
            sampler_stages: [
              { sampler: "euler", scheduler: "normal", steps: 22, cfg: 6 },
            ],
          },
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.modes.value()).toEqual(promptSelectionState);
    expect(fixture.modes.applyState).toHaveBeenCalledWith(promptSelectionState);
    expect(fixture.api.put).toHaveBeenCalledWith(
      "playground/generator-state",
      {
        ...promptSelectionState,
        checkpoint: "model",
        seed_mode: "fixed",
      },
      expect.any(Object),
    );
    expect(intentStore.read()).toEqual({ renderImageUid: "image-render" });
    expect(
      fixture.api.post.mock.calls.some(
        ([path]) => path === "playground/drafts",
      ),
    ).toBe(false);

    await fixture.controller.prepare();
    expect(fixture.api.post).toHaveBeenCalledWith(
      "playground/drafts",
      {
        ...promptSelectionState,
        generation: expect.any(Object),
      },
      expect.any(Object),
    );
  });

  it("rolls back a rejected image prompt without persisting or clearing its source", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    const previousPromptState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-existing",
          revision_uid: "character-existing-rev",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      savedState: previousPromptState,
      selectionValue: previousPromptState,
      modeStateRejection: (state) =>
        state.selections?.some(
          (selection) => selection.component_uid === "unavailable-scene",
        ) || state.loras?.some((lora) => lora.lora_uid === "unavailable-lora")
          ? ["scene", "loras"]
          : [],
      image: {
        prompt_setup: {
          selections: [
            {
              kind: "character",
              component_uid: "character-new",
              revision_uid: "character-rev-1",
              position: 0,
            },
            {
              kind: "scene",
              component_uid: "unavailable-scene",
              revision_uid: "scene-rev-1",
              position: 1,
            },
          ],
          loras: [
            {
              lora_uid: "unavailable-lora",
              provider_name: "missing",
              model_strength: 1,
              clip_strength: 1,
              model_effective: true,
              clip_effective: true,
            },
          ],
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.modes.value()).toEqual(previousPromptState);
    expect(fixture.modes.applyState).toHaveBeenCalledTimes(3);
    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    expect(fixture.status.textContent).toContain("scene, loras");
  });

  it("visibly rejects a typed handoff without its required character", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      image: {
        prompt_setup: {
          selections: [
            {
              kind: "scene",
              component_uid: "scene-a",
              revision_uid: "scene-rev-1",
              position: 0,
            },
          ],
          loras: [],
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.status.textContent).toContain(
      "Character-Prompt-Auswahl fehlt",
    );
    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
  });

  it("restores the prior prompt and retains staging when immediate state persistence fails", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    const previousPromptState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-existing",
          revision_uid: "character-existing-rev",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      savedState: previousPromptState,
      selectionValue: previousPromptState,
      stateSaveError: new Error("state save kaputt"),
      image: {
        prompt_setup: {
          selections: [
            {
              kind: "character",
              component_uid: "character-new",
              revision_uid: "character-rev-1",
              position: 0,
            },
          ],
          loras: [],
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.modes.value()).toEqual(previousPromptState);
    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    expect(fixture.status.textContent).toContain("state save kaputt");
  });

  it("rolls back through the public state API when editor application throws", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    const previousPromptState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-existing",
          revision_uid: "character-existing-rev",
        },
      ],
      loras: [],
    };
    let attemptedNewState = false;
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      savedState: previousPromptState,
      selectionValue: previousPromptState,
      modeStateError: (state) => {
        if (
          state.selections?.some(
            (selection) => selection.component_uid === "character-new",
          )
        ) {
          attemptedNewState = true;
          return new Error("editor apply kaputt");
        }
        if (
          attemptedNewState &&
          state.selections?.some(
            (selection) => selection.component_uid === "character-existing",
          )
        )
          return new Error("rollback kaputt");
        return null;
      },
      image: {
        prompt_setup: {
          selections: [
            {
              kind: "character",
              component_uid: "character-new",
              revision_uid: "character-rev-1",
              position: 0,
            },
          ],
          loras: [],
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    expect(fixture.status.textContent).toContain("rollback kaputt");
  });

  it("reports prompt-source cleanup failures after a successful state save", async () => {
    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    vi.spyOn(intentStore, "clearPromptImage").mockImplementation(() => {
      throw new Error("storage kaputt");
    });
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      image: {
        prompt_setup: {
          selections: [
            {
              kind: "character",
              component_uid: "character-a",
              revision_uid: "character-rev-1",
              position: 0,
            },
          ],
          loras: [],
        },
      },
    });

    await fixture.controller.start();

    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    expect(fixture.status.textContent).toContain("storage kaputt");
  });

  it("rejects malformed typed prompt ordering and identities visibly", async () => {
    const invalidSelections = [
      {
        message: "Prompt-Reihenfolge ist ungültig",
        selections: [
          {
            kind: "character",
            component_uid: "character-a",
            revision_uid: "character-rev-1",
            position: 0,
          },
          {
            kind: "scene",
            component_uid: "scene-a",
            revision_uid: "scene-rev-1",
            position: -1,
          },
        ],
      },
      {
        message: "Unbekannte Prompt-Rolle",
        selections: [
          {
            kind: "character",
            component_uid: "character-a",
            revision_uid: "character-rev-1",
            position: 0,
          },
          {
            kind: "unknown",
            component_uid: "unknown-a",
            revision_uid: "unknown-rev",
            position: 1,
          },
        ],
      },
      {
        message: "Prompt-Rolle mehrfach vorhanden: character",
        selections: [
          {
            kind: "character",
            component_uid: "character-a",
            revision_uid: "character-rev-1",
            position: 0,
          },
          {
            kind: "character",
            component_uid: "character-b",
            revision_uid: "character-rev-2",
            position: 1,
          },
        ],
      },
      {
        message: "Prompt-Rolle unvollständig: scene",
        selections: [
          {
            kind: "character",
            component_uid: "character-a",
            revision_uid: "character-rev-1",
            position: 0,
          },
          {
            kind: "scene",
            component_uid: "",
            revision_uid: "scene-rev-1",
            position: 1,
          },
        ],
      },
    ];

    for (const invalid of invalidSelections) {
      const intentStore = new PlaygroundIntentStore(new MemoryStorage());
      intentStore.stagePromptImage("image-prompt");
      const fixture = createFixture({
        intent: intentStore.read(),
        intentStore,
        image: {
          prompt_setup: { selections: invalid.selections, loras: [] },
        },
      });

      await fixture.controller.start();

      expect(fixture.status.textContent).toContain(invalid.message);
      expect(fixture.api.put).not.toHaveBeenCalled();
      expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    }
  });

  it("rejects malformed LoRA handoff data and permits an absent empty list", async () => {
    const malformedLoras = [
      {
        loras: "not-an-array",
        message: "LoRA-Setup des Bildes ist ungültig",
      },
      {
        loras: [{ lora_uid: "lora-style" }],
        message: "LoRA-Wirksamkeit des Bildes ist nicht verfügbar",
      },
      {
        loras: [
          {
            lora_uid: "lora-style",
            model_effective: true,
            clip_effective: true,
            model_strength: "invalid",
            clip_strength: 1,
          },
        ],
        message: "LoRA-Stärken des Bildes sind ungültig",
      },
    ];
    const characterSelection = [
      {
        kind: "character",
        component_uid: "character-a",
        revision_uid: "character-rev-1",
        position: 0,
      },
    ];

    for (const invalid of malformedLoras) {
      const intentStore = new PlaygroundIntentStore(new MemoryStorage());
      intentStore.stagePromptImage("image-prompt");
      const fixture = createFixture({
        intent: intentStore.read(),
        intentStore,
        image: {
          prompt_setup: {
            selections: characterSelection,
            loras: invalid.loras,
          },
        },
      });

      await fixture.controller.start();

      expect(fixture.status.textContent).toContain(invalid.message);
      expect(fixture.api.put).not.toHaveBeenCalled();
      expect(intentStore.read()).toEqual({ promptImageUid: "image-prompt" });
    }

    const intentStore = new PlaygroundIntentStore(new MemoryStorage());
    intentStore.stagePromptImage("image-prompt");
    const fixture = createFixture({
      intent: intentStore.read(),
      intentStore,
      image: {
        prompt_setup: { selections: characterSelection },
      },
    });

    await fixture.controller.start();

    expect(fixture.modes.value().loras).toEqual([]);
    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(intentStore.read()).toEqual({});
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
  let activeSelectionValue = options.selectionValue || { selections: [] };
  const modes = disposable({
    render: vi.fn(),
    applyState: vi.fn((state) => {
      activeSelectionValue = {
        selections: state.selections || activeSelectionValue.selections || [],
        ...(state.loras !== undefined ||
        activeSelectionValue.loras !== undefined
          ? { loras: state.loras || activeSelectionValue.loras || [] }
          : {}),
      };
      const error = options.modeStateError?.(state);
      if (error) throw error;
      return options.modeStateRejection?.(state) || options.stateRejected || [];
    }),
    applyIntent: vi.fn(() => options.intentRejected || []),
    showResolvedComponents: vi.fn(),
    value: vi.fn(() => activeSelectionValue),
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
      if (path.startsWith("images/")) {
        const imageUid = decodeURIComponent(
          path.slice("images/".length, -"/generator-handoff".length),
        );
        return Promise.resolve(
          options.images?.[imageUid] || options.image || {},
        );
      }
      return Promise.resolve(
        path === "playground/components"
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

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }
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
