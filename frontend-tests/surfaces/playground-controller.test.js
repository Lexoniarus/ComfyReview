import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { DraftSession } from "../../static/js/playground/draft-session.js";
import { GeneratorHandoffApplier } from "../../static/js/playground/generator-handoff-applier.js";
import {
  GeneratorHandoffUrlCleaner,
  readPlaygroundIntent,
} from "../../static/js/playground/playground-intent.js";
import { GeneratorStatePersistence } from "../../static/js/playground/generator-state-persistence.js";
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
    expect(fixture.controls.applyIntent).not.toHaveBeenCalled();

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

  it("consumes a successful non-prompt render prefill", async () => {
    const fixture = createFixture({
      intent: { sampler: "euler" },
    });

    await fixture.controller.start();

    expect(fixture.controls.applyIntent).toHaveBeenCalledWith(
      expect.objectContaining({ sampler: "euler" }),
    );
    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(fixture.urlCleaner.removeHandoff).toHaveBeenCalledOnce();
  });

  it("rejects inapplicable image render setups without changing controls", async () => {
    for (const renderSetup of [
      { applicable: false, issues: ["checkpoint", "upscale_model"] },
      { applicable: false },
    ]) {
      const fixture = createFixture({
        intent: { renderImageUid: "image-render" },
        image: { render_setup: renderSetup },
      });

      await fixture.controller.start();

      expect(fixture.api.put).not.toHaveBeenCalled();
      expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
      expect(fixture.status.textContent).toContain(
        renderSetup.issues ? "checkpoint, upscale_model" : "nicht anwendbar",
      );
    }
  });

  it("rejects multiple typed prompt sources before changing generator state", async () => {
    const cases = [
      {
        prompt: {
          promptImageUid: "image-a",
          promptCompositionUid: "composition-a",
        },
      },
      {
        prompt: {
          promptCompositionUid: "composition-a",
          promptScope: {
            kind: "scene",
            component_uid: "scene-a",
            revision_uid: "scene-revision-a",
          },
        },
      },
      {
        prompt: {
          promptCombination: [
            { kind: "scene", component_uid: "scene-a" },
            { kind: "outfit", component_uid: "outfit-a" },
          ],
          promptScope: {
            kind: "character",
            component_uid: "character-a",
            revision_uid: null,
          },
        },
      },
    ];

    for (const { prompt } of cases) {
      const intentUrlCleaner = {
        removeHandoff: vi.fn(),
      };
      const existingPromptState = {
        selections: [
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-existing",
            revision_uid: "character-existing-revision",
          },
        ],
        loras: [],
      };
      const fixture = createFixture({
        intent: { ...prompt, renderImageUid: "render-image" },
        intentUrlCleaner,
        selectionValue: existingPromptState,
        savedState: {
          selections: [
            {
              kind: "character",
              mode: "fixed",
              component_uid: "character-persisted",
              revision_uid: "character-persisted-revision",
            },
          ],
        },
      });

      await fixture.controller.start();

      expect(fixture.status.textContent).toContain(
        "Mehrdeutiger Prompt-Handoff",
      );
      expect(fixture.modes.render).toHaveBeenCalledOnce();
      expect(fixture.controls.render).toHaveBeenCalledOnce();
      expect(fixture.api.put).not.toHaveBeenCalled();
      expect(
        fixture.api.post.mock.calls.some(
          ([path]) => path === "playground/drafts",
        ),
      ).toBe(false);
      expect(fixture.modes.value()).toEqual({
        selections: [
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-persisted",
            revision_uid: "character-persisted-revision",
          },
        ],
        loras: [],
      });
      expect(intentUrlCleaner.removeHandoff).not.toHaveBeenCalled();
      expect(fixture.prepareButton.disabled).toBe(false);
      expect(fixture.submitButton.disabled).toBe(true);
    }
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
    await generationFailure.controller.prepare();
    await generationFailure.controller.submit();
    expect(generationFailure.result.dataset.state).toBe("error");
    expect(generationFailure.result.textContent).toBe("comfy kaputt");

    const generationAbort = createFixture({
      generationError: new DOMException("aborted", "AbortError"),
    });
    await generationAbort.controller.start();
    await generationAbort.controller.prepare();
    await generationAbort.controller.submit();
    expect(generationAbort.result.textContent).toBe("");
    expect(generationAbort.result.dataset.state).toBeUndefined();

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

    const evidenceFailure = createFixture({
      evidenceError: new Error("evidence kaputt"),
    });
    await evidenceFailure.controller.refreshEvidence();
    expect(evidenceFailure.status.textContent).toBe("evidence kaputt");

    const evidenceAbort = createFixture({
      evidenceError: new DOMException("aborted", "AbortError"),
    });
    await evidenceAbort.controller.refreshEvidence();
    expect(evidenceAbort.status.textContent).toBe("");
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
    await fixture.controller.prepare();
    await fixture.controller.submit();

    expect(fixture.result.textContent).toContain("generation-2 · submitted");
    expect(fixture.status.textContent).toBe(
      "2 Generierungen an ComfyUI übergeben",
    );
  });

  it("applies typed image prompt selections and all canonical LoRAs without creating a draft", async () => {
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
          clip_strength: 0.8,
        },
        {
          lora_uid: "lora-unused",
          revision_uid: "lora-rev-unused",
          provider_name: "unused.safetensors",
          model_strength: 0.9,
          clip_strength: 0.6,
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
      intent: { promptImageUid: "image-prompt" },
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
    expect(fixture.urlCleaner.removeHandoff).toHaveBeenCalledOnce();
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
      intent: { promptImageUid: "image-prompt" },
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
              revision_uid: "unavailable-lora-revision",
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
    expect(fixture.modes.applyState).toHaveBeenCalled();
    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
    expect(fixture.status.textContent).toContain("scene, loras");
  });

  it("visibly rejects a typed handoff without its required character", async () => {
    const fixture = createFixture({
      intent: { promptImageUid: "image-prompt" },
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
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
  });

  it("restores the prior prompt and retains staging when immediate state persistence fails", async () => {
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
      intent: { promptImageUid: "image-prompt" },
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
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
    expect(fixture.status.textContent).toContain("state save kaputt");
  });

  it("rolls back through the public state API when editor application throws", async () => {
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
      intent: { promptImageUid: "image-prompt" },
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
      controlStateError: (state) =>
        state.checkpoint === "model"
          ? new Error("controls rollback kaputt")
          : null,
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
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
    expect(fixture.status.textContent).toContain("rollback kaputt");
    expect(fixture.status.textContent).toContain("controls rollback kaputt");
  });

  it("reports prompt-source cleanup failures after a successful state save", async () => {
    const intentUrlCleaner = {
      removeHandoff: vi.fn(() => {
        throw new Error("URL kaputt");
      }),
    };
    const fixture = createFixture({
      intent: { promptImageUid: "image-prompt" },
      intentUrlCleaner,
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
    expect(fixture.modes.value().selections).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ component_uid: "character-a" }),
      ]),
    );
    expect(fixture.status.textContent).toContain("URL kaputt");
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
      const fixture = createFixture({
        intent: { promptImageUid: "image-prompt" },
        image: {
          prompt_setup: { selections: invalid.selections, loras: [] },
        },
      });

      await fixture.controller.start();

      expect(fixture.status.textContent).toContain(invalid.message);
      expect(fixture.api.put).not.toHaveBeenCalled();
      expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
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
        message: "LoRA-Identität des Bildes ist unvollständig",
      },
      {
        loras: [
          {
            lora_uid: "lora-style",
            revision_uid: "lora-style-revision",
            provider_name: "style.safetensors",
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
      const fixture = createFixture({
        intent: { promptImageUid: "image-prompt" },
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
      expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
    }

    const fixture = createFixture({
      intent: { promptImageUid: "image-prompt" },
      image: {
        prompt_setup: { selections: characterSelection },
      },
    });

    await fixture.controller.start();

    expect(fixture.modes.value().loras).toEqual([]);
    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(fixture.urlCleaner.removeHandoff).toHaveBeenCalledOnce();
  });

  it("applies a complete composition as the normal exact generator state", async () => {
    const fixture = createFixture({
      intent: { promptCompositionUid: "composition-exact" },
      savedState: {
        selections: [
          {
            kind: "modifier",
            mode: "fixed",
            component_uid: "modifier-old",
            revision_uid: "modifier-old-revision",
          },
        ],
        loras: [{ lora_uid: "stale-lora" }],
      },
      compositionHandoff: {
        selections: [
          {
            kind: "character",
            component_uid: "character-a",
            revision_uid: "character-revision-historical",
          },
          {
            kind: "scene",
            component_uid: "scene-a",
            revision_uid: "scene-revision-historical",
          },
        ],
      },
    });

    await fixture.controller.start();

    expect(fixture.api.get).toHaveBeenCalledWith(
      "playground/compositions/composition-exact/prompt-selections",
      expect.any(Object),
    );
    expect(fixture.modes.value().selections).toEqual(
      expect.arrayContaining([
        {
          kind: "character",
          component_uid: "character-a",
          revision_uid: "character-revision-historical",
          mode: "fixed",
        },
        {
          kind: "scene",
          component_uid: "scene-a",
          revision_uid: "scene-revision-historical",
          mode: "fixed",
        },
        {
          kind: "modifier",
          component_uid: null,
          revision_uid: null,
          mode: "off",
        },
      ]),
    );
    expect(fixture.modes.value().loras).toEqual([]);
    expect(fixture.api.put).toHaveBeenCalledWith(
      "playground/generator-state",
      expect.objectContaining({
        selections: expect.any(Array),
        loras: [],
      }),
      expect.any(Object),
    );
    expect(
      fixture.controls.applyIntent.mock.invocationCallOrder[0],
    ).toBeLessThan(fixture.api.put.mock.invocationCallOrder[0]);
    expect(fixture.urlCleaner.removeHandoff).toHaveBeenCalledOnce();
    expect(
      fixture.api.post.mock.calls.some(
        ([path]) => path === "playground/drafts",
      ),
    ).toBe(false);

    await fixture.controller.prepare();
    const draftCall = fixture.api.post.mock.calls.find(
      ([path]) => path === "playground/drafts",
    );
    expect(draftCall[1]).toEqual(
      expect.objectContaining({
        selections: expect.arrayContaining([
          expect.objectContaining({
            kind: "character",
            revision_uid: "character-revision-historical",
          }),
          expect.objectContaining({
            kind: "scene",
            revision_uid: "scene-revision-historical",
          }),
        ]),
      }),
    );
    expect(draftCall[1]).not.toHaveProperty("composition_uid");
    expect(draftCall[1]).not.toHaveProperty("revision_uids");
  });

  it("applies one exact scope selection as a partial prompt patch", async () => {
    const promptScope = {
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: "scene-revision-historical",
    };
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-a",
          revision_uid: "character-revision-a",
        },
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-old",
          revision_uid: "scene-revision-old",
        },
        {
          kind: "modifier",
          mode: "fixed",
          component_uid: "modifier-a",
          revision_uid: "modifier-revision-a",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: { promptScope },
      savedState,
    });

    await fixture.controller.start();

    expect(fixture.modes.applyState).toHaveBeenLastCalledWith({
      selections: [
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: "scene-revision-historical",
        },
      ],
    });
    const byKind = new Map(
      fixture.modes
        .value()
        .selections.map((selection) => [selection.kind, selection]),
    );
    expect(byKind.get("scene")).toEqual({
      kind: "scene",
      mode: "fixed",
      component_uid: "scene-a",
      revision_uid: "scene-revision-historical",
    });
    expect(byKind.get("character")).toEqual(savedState.selections[0]);
    expect(byKind.get("modifier")).toEqual(savedState.selections[2]);
    expect(fixture.urlCleaner.removeHandoff).toHaveBeenCalledOnce();

    await fixture.controller.prepare();
    const draftCall = fixture.api.post.mock.calls.find(
      ([path]) => path === "playground/drafts",
    );
    expect(draftCall[1].selections).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          kind: "scene",
          revision_uid: "scene-revision-historical",
        }),
      ]),
    );
    expect(draftCall[1]).not.toHaveProperty("composition_uid");
  });

  it("applies, persists, and removes all handoff query parameters", async () => {
    const selections = [
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
      { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
    ];
    const locationRef = {
      href: `https://example.test/playground/generator?prompt_combination=${encodeURIComponent(
        JSON.stringify(selections),
      )}&sampler=euler&view=cards`,
    };
    const historyRef = {
      state: null,
      replaceState: vi.fn((_state, _title, path) => {
        locationRef.href = new URL(path, locationRef.href).href;
      }),
    };
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-a",
          revision_uid: "character-revision-a",
        },
        {
          kind: "pose",
          mode: "fixed",
          component_uid: "pose-a",
          revision_uid: "pose-revision-a",
        },
      ],
      loras: [{ lora_uid: "existing-lora" }],
    };
    const fixture = createFixture({
      intent: readPlaygroundIntent(new URL(locationRef.href).search),
      intentUrlCleaner: new GeneratorHandoffUrlCleaner(locationRef, historyRef),
      savedState,
      selectionValue: savedState,
    });

    await fixture.controller.start();

    expect(fixture.modes.applyState).toHaveBeenLastCalledWith({
      selections: selections.map((selection) => ({
        ...selection,
        mode: "fixed",
      })),
    });
    const appliedByKind = new Map(
      fixture.modes
        .value()
        .selections.map((selection) => [selection.kind, selection]),
    );
    expect(appliedByKind.get("scene")).toEqual({
      kind: "scene",
      mode: "fixed",
      component_uid: "scene-a",
      revision_uid: null,
    });
    expect(appliedByKind.get("outfit")).toEqual({
      kind: "outfit",
      mode: "fixed",
      component_uid: "outfit-a",
      revision_uid: null,
    });
    expect(appliedByKind.get("character")).toEqual(savedState.selections[0]);
    expect(appliedByKind.get("pose")).toEqual(savedState.selections[1]);
    expect(fixture.modes.value().loras).toEqual(savedState.loras);
    expect(fixture.api.put).toHaveBeenCalledWith(
      "playground/generator-state",
      expect.objectContaining({
        selections: expect.any(Array),
        loras: savedState.loras,
      }),
      expect.any(Object),
    );
    const currentUrl = new URL(locationRef.href);
    expect(currentUrl.searchParams.has("prompt_combination")).toBe(false);
    expect(currentUrl.searchParams.has("sampler")).toBe(false);
    expect(currentUrl.searchParams.get("view")).toBe("cards");
    expect(historyRef.replaceState).toHaveBeenCalledOnce();
    const reloadedIntent = {
      ...readPlaygroundIntent(currentUrl.search),
    };
    expect(reloadedIntent.promptCombination).toBeUndefined();

    expect(
      fixture.api.post.mock.calls.some(
        ([path]) => path === "playground/drafts",
      ),
    ).toBe(false);
    await fixture.controller.prepare();
    const draftCall = fixture.api.post.mock.calls.find(
      ([path]) => path === "playground/drafts",
    );
    expect(draftCall[1]).toEqual(
      expect.objectContaining({
        selections: expect.arrayContaining(
          selections.map((selection) =>
            expect.objectContaining({
              kind: selection.kind,
              component_uid: selection.component_uid,
            }),
          ),
        ),
      }),
    );
    expect(draftCall[1]).not.toHaveProperty("componentUids");
    expect(draftCall[1]).not.toHaveProperty("composition_uid");
    expect(draftCall[1]).not.toHaveProperty("revision_uids");
  });

  it("retains Combination staging and URL when selection application is rejected", async () => {
    const selections = [
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
      {
        kind: "outfit",
        component_uid: "outfit-unavailable",
        revision_uid: null,
      },
    ];
    const locationRef = {
      href: `https://example.test/playground/generator?prompt_combination=${encodeURIComponent(
        JSON.stringify(selections),
      )}`,
    };
    const historyRef = { state: null, replaceState: vi.fn() };
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-before",
          revision_uid: "character-before-revision",
        },
      ],
      loras: [{ lora_uid: "existing-lora" }],
    };
    const fixture = createFixture({
      intent: readPlaygroundIntent(new URL(locationRef.href).search),
      intentUrlCleaner: new GeneratorHandoffUrlCleaner(locationRef, historyRef),
      savedState,
      selectionValue: savedState,
      modeStateRejection: (state) =>
        state.selections.length === 2 ? ["outfit"] : [],
    });

    await fixture.controller.start();

    expect(fixture.status.textContent).toContain("outfit");
    expect(fixture.modes.value()).toEqual(savedState);
    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(historyRef.replaceState).not.toHaveBeenCalled();
    expect(
      new URL(locationRef.href).searchParams.has("prompt_combination"),
    ).toBe(true);
  });

  it("leaves Combination staging and URL intact when generator-state persistence fails", async () => {
    const selections = [
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
      { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
    ];
    const locationRef = {
      href: `https://example.test/playground/generator?prompt_combination=${encodeURIComponent(
        JSON.stringify(selections),
      )}`,
    };
    const historyRef = { state: null, replaceState: vi.fn() };
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-before",
          revision_uid: "character-before-revision",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: readPlaygroundIntent(new URL(locationRef.href).search),
      intentUrlCleaner: new GeneratorHandoffUrlCleaner(locationRef, historyRef),
      savedState,
      selectionValue: savedState,
      stateSaveError: new Error("persist failed"),
    });

    await fixture.controller.start();

    expect(fixture.status.textContent).toContain("persist failed");
    expect(fixture.modes.value()).toEqual(savedState);
    expect(fixture.api.put).toHaveBeenCalledOnce();
    expect(historyRef.replaceState).not.toHaveBeenCalled();
    expect(
      new URL(locationRef.href).searchParams.has("prompt_combination"),
    ).toBe(true);
  });

  it("retains a typed composition source and restores state after persistence fails", async () => {
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-before",
          revision_uid: "character-before-revision",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: { promptCompositionUid: "composition-failed" },
      savedState,
      stateSaveError: new Error("persist failed"),
      compositionHandoff: {
        selections: [
          {
            kind: "character",
            component_uid: "character-after",
            revision_uid: "character-after-revision",
          },
        ],
      },
    });

    await fixture.controller.start();

    expect(fixture.status.textContent).toContain("persist failed");
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
    expect(fixture.modes.value().selections).toEqual(savedState.selections);
  });

  it("rejects an incomplete composition without changing or clearing the prompt", async () => {
    const savedState = {
      selections: [
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-before",
          revision_uid: "character-before-revision",
        },
      ],
      loras: [],
    };
    const fixture = createFixture({
      intent: { promptCompositionUid: "composition-no-character" },
      savedState,
      compositionHandoff: {
        selections: [
          {
            kind: "scene",
            component_uid: "scene-a",
            revision_uid: "scene-revision-a",
          },
        ],
      },
    });

    await fixture.controller.start();

    expect(fixture.status.textContent).toContain(
      "Character-Prompt-Auswahl fehlt",
    );
    expect(fixture.modes.value().selections).toEqual(savedState.selections);
    expect(fixture.api.put).not.toHaveBeenCalled();
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
  });

  it("keeps rejected image handoff parameters and resolves independent packages", async () => {
    const fixture = createFixture({
      intent: {
        promptImageUid: "image-prompt",
        renderImageUid: "image-render",
      },
      intentRejected: ["checkpoint"],
      image: {
        prompt_setup: {
          source_image_uid: "image-prompt",
          selections: [
            {
              kind: "character",
              component_uid: "character-a",
              revision_uid: "revision-character-a",
              position: 0,
            },
          ],
          loras: [],
        },
        render_setup: {
          applicable: true,
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
    expect(fixture.urlCleaner.removeHandoff).not.toHaveBeenCalled();
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
      fixture.controller.promptSettingsChanged();
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
  const selectionSnapshots = new WeakSet();
  const modes = disposable({
    render: vi.fn(),
    applyState: vi.fn((state) => {
      const error = options.modeStateError?.(state);
      if (error) throw error;
      if (selectionSnapshots.has(state)) {
        activeSelectionValue = state;
        return [];
      }
      const incomingSelections = Array.isArray(state.selections)
        ? state.selections
        : [];
      const currentByKind = new Map(
        (activeSelectionValue.selections || []).map((selection) => [
          selection.kind,
          selection,
        ]),
      );
      if (incomingSelections.length === 7) {
        currentByKind.clear();
      }
      for (const selection of incomingSelections) {
        currentByKind.set(selection.kind, selection);
      }
      activeSelectionValue = {
        selections: Array.from(currentByKind.values()),
        ...(state.loras !== undefined ||
        activeSelectionValue.loras !== undefined
          ? { loras: state.loras || activeSelectionValue.loras || [] }
          : {}),
      };
      return options.modeStateRejection?.(state) || options.stateRejected || [];
    }),
    showResolvedComponents: vi.fn(),
    setBusy: vi.fn(),
    value: vi.fn(() => {
      selectionSnapshots.add(activeSelectionValue);
      return activeSelectionValue;
    }),
  });
  const controls = disposable({
    render: vi.fn(),
    applyState: vi.fn((state) => {
      const error = options.controlStateError?.(state);
      if (error) throw error;
      return options.stateRejected || [];
    }),
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
    clear: vi.fn(),
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
      if (path.startsWith("playground/compositions/")) {
        return options.compositionLoadError
          ? Promise.reject(options.compositionLoadError)
          : Promise.resolve(options.compositionHandoff || { selections: [] });
      }
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
        return options.evidenceError
          ? Promise.reject(options.evidenceError)
          : Promise.resolve({ prompt_match: null, sampler_match: null });
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
  const persistence = new GeneratorStatePersistence({
    api,
    snapshot: () => ({
      ...modes.value(),
      ...controls.stateValue(),
    }),
    onError: (error) => {
      status.textContent = `Einstellungen konnten nicht gespeichert werden: ${error.message}`;
    },
  });
  const handoffRequests = new RequestLifecycle();
  const urlCleaner = options.intentUrlCleaner || { removeHandoff: vi.fn() };
  const handoffApplier = new GeneratorHandoffApplier({
    api,
    modes,
    controls,
    persistence,
    requests: handoffRequests,
    urlCleaner,
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
    persistence,
    handoffApplier,
    draftSession: new DraftSession(new RequestLifecycle()),
    prepareButton,
    submitButton,
    status,
    result,
    intent: options.intent,
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
    urlCleaner,
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
