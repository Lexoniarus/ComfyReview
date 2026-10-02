import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftPreview } from "../../static/js/playground/draft-preview.js";
import { GenerationControls } from "../../static/js/playground/generation-controls.js";
import { PromptModeEditor } from "../../static/js/playground/prompt-mode-editor.js";
import { TopCombinationsView } from "../../static/js/playground/top-combinations.js";

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
        batch_runs: 1,
        randomize_seed: false,
        steps_max: 24,
        cfg_max: 6.5,
        cfg_step: 0.1,
      },
    });
    const seedMode = root.querySelector('[data-field="seed_mode"]');
    const seed = root.querySelector('[data-field="seed"]');
    seedMode.value = "random";
    seedMode.dispatchEvent(new Event("change"));
    expect(seed.disabled).toBe(true);
    expect(controls.value().sampler.randomize_seed).toBe(true);
    controls.setBusy(true);
    expect(root.querySelector("select")?.disabled).toBe(true);
    controls.setBusy(false);
    expect(seed.disabled).toBe(true);
    controls.dispose();
  });

  it("keeps edits as draft overrides and builds the UID-based payload", () => {
    const root = document.createElement("div");
    const state = document.createElement("span");
    const onChange = vi.fn();
    const preview = new DraftPreview(root, state, onChange);
    expect(preview.generationPayload({})).toBeNull();
    expect(preview.promptPayload()).toBeNull();

    preview.render(
      {
        components,
        positive_prompt: "positive",
        negative_prompt: "negative",
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [{ text: "negative", weight: 1 }],
        revision_uids: ["revision-character-a"],
        draft_overridden: false,
      },
      "draft-1",
    );
    expect(state.textContent).toBe("Katalogrevisionen unverändert");
    expect(root.textContent).toContain("Serverseitig gerenderter Prompt");
    expect(
      root.querySelector(".draft-rendered-snapshots").textContent,
    ).toContain("positive");
    const positive = root.querySelector("[data-atom-text]");
    positive.value = "edited";
    positive.dispatchEvent(new Event("input"));
    const negative = root.querySelectorAll("[data-atom-text]")[1];
    negative.dispatchEvent(new Event("input"));
    expect(state.textContent).toBe("Draft-Override aktiv");
    expect(onChange).toHaveBeenCalled();
    expect(preview.promptPayload().positive_atoms[0].text).toBe("edited");
    preview.renderSnapshots({
      positive_prompt: "server edited",
      negative_prompt: "server negative",
    });
    expect(root.textContent).toContain("server edited");

    expect(
      preview.generationPayload({
        checkpoint: "model.safetensors",
        sampler: { seed: 1 },
      }),
    ).toEqual(
      expect.objectContaining({
        draft_uid: "draft-1",
        component_uids: components.map((item) => item.component_uid),
        positive_atoms: [{ text: "edited", weight: 1 }],
      }),
    );

    preview.render(
      {
        components: [component("scene-a", "scene", "Scene")],
        positive_prompt: "positive",
        negative_prompt: "negative",
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [{ text: "negative", weight: 1 }],
        draft_overridden: true,
      },
      "draft-2",
    );
    expect(preview.generationPayload({})).toBeNull();
    preview.dispose();

    const defaultRoot = document.createElement("div");
    const defaultPreview = new DraftPreview(
      defaultRoot,
      document.createElement("span"),
    );
    defaultPreview.render(
      {
        components,
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [],
      },
      "draft-default",
    );
    defaultRoot
      .querySelector("[data-atom-text]")
      .dispatchEvent(new Event("input"));
    defaultPreview.dispose();
  });

  it("renders separate top two- and three-component evidence", () => {
    const root = document.createElement("div");
    const view = new TopCombinationsView(root);

    view.render({
      two_component: [
        {
          label: "Aiko + Rooftop",
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
          best_images: [{ url: "best.png" }, { url: "" }],
        },
        null,
      ],
      three_component: [],
    });

    expect(root.textContent).toContain("Top 2er-Kombinationen");
    expect(root.textContent).toContain("Charakter + Szene + Outfit");
    expect(root.textContent).toContain("Aiko + Rooftop");
    expect(root.textContent).toContain("2 Bilder · 4 Bewertungen · Ø 8,5 / 10");
    expect(root.textContent).toContain("Noch keine ausreichend belegten");
    expect(root.textContent).toContain("Unbenannte Kombination");
    expect(root.textContent).toContain("Kein Bildbeispiel");
    expect(root.querySelector("img")?.getAttribute("src")).toBe("best.png");

    view.dispose();
    expect(root.children).toHaveLength(0);
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
