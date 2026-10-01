import { beforeEach, describe, expect, it } from "vitest";

import { DraftPreview } from "../../static/js/playground/draft-preview.js";
import { GenerationControls } from "../../static/js/playground/generation-controls.js";
import { PromptModeEditor } from "../../static/js/playground/prompt-mode-editor.js";

const components = [
  component("character-a", "character", "Aiko"),
  component("scene-a", "scene", "Rooftop"),
  component("outfit-a", "outfit", "Uniform"),
  component("pose-a", "pose", "Standing"),
  component("expression-a", "expression", "Smile"),
  component("lighting-a", "lighting", "Sunset"),
  component("modifier-a", "modifier", "Wind"),
];

describe("Playground browser components", () => {
  beforeEach(() => document.body.replaceChildren());

  it("owns complete fixed, random and off prompt-role intent", () => {
    const root = document.createElement("div");
    const seed = document.createElement("input");
    seed.value = "23";
    const editor = new PromptModeEditor(root, seed);

    editor.render(components);
    const rows = root.querySelectorAll(".prompt-mode-row");
    expect(rows).toHaveLength(7);
    expect(rows[0].querySelector("select")?.value).toBe("fixed");

    const sceneMode = rows[1].querySelector("select");
    sceneMode.value = "off";
    sceneMode.dispatchEvent(new Event("change"));
    expect(rows[1].querySelectorAll("select")[1].disabled).toBe(true);
    expect(editor.value()).toEqual(
      expect.objectContaining({
        seed: 23,
        selections: expect.arrayContaining([
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-a",
          },
          { kind: "scene", mode: "off", component_uid: null },
        ]),
      }),
    );
    seed.value = "invalid";
    expect(editor.value().seed).toBeNull();
    editor.dispose();
  });

  it("renders blueprint defaults and returns typed generation controls", () => {
    const root = document.createElement("div");
    const controls = new GenerationControls(root);
    controls.render({
      checkpoints: ["model.safetensors"],
      samplers: ["euler"],
      schedulers: ["normal"],
      defaults: {
        checkpoint: "model.safetensors",
        seed: 7,
        steps: 24,
        cfg: 6.5,
        sampler: "euler",
        scheduler: "normal",
        denoise: 1,
      },
    });

    expect(controls.value()).toEqual({
      checkpoint: "model.safetensors",
      sampler: {
        seed: 7,
        steps: 24,
        cfg: 6.5,
        sampler: "euler",
        scheduler: "normal",
        denoise: 1,
      },
    });
    controls.setBusy(true);
    expect(root.querySelector("select")?.disabled).toBe(true);
    controls.setBusy(false);
    controls.dispose();
  });

  it("keeps edits as draft overrides and builds the UID-based payload", () => {
    const root = document.createElement("div");
    const state = document.createElement("span");
    const preview = new DraftPreview(root, state);
    expect(preview.generationPayload({})).toBeNull();

    preview.render(
      {
        components,
        positive_prompt: "positive",
        negative_prompt: "negative",
        revision_uids: ["revision-character-a"],
        draft_overridden: false,
      },
      "draft-1",
    );
    expect(state.textContent).toBe("Katalogrevisionen unverändert");
    const positive = root.querySelector("[data-prompt='positive']");
    positive.value = "edited";
    positive.dispatchEvent(new Event("input"));
    expect(state.textContent).toBe("Draft-Override aktiv");

    expect(
      preview.generationPayload({
        checkpoint: "model.safetensors",
        sampler: { seed: 1 },
      }),
    ).toEqual(
      expect.objectContaining({
        draft_uid: "draft-1",
        character_component_uid: "character-a",
        positive_prompt: "edited",
        revision_uids: ["revision-character-a"],
        draft_overridden: true,
      }),
    );

    preview.render(
      {
        components: [component("scene-a", "scene", "Scene")],
        positive_prompt: "positive",
        negative_prompt: "negative",
        draft_overridden: true,
      },
      "draft-2",
    );
    expect(preview.generationPayload({})).toBeNull();
    preview.dispose();
  });
});

function component(componentUid, kind, name) {
  return {
    component_uid: componentUid,
    kind,
    name,
    latest_revision: { revision_number: 1 },
  };
}
