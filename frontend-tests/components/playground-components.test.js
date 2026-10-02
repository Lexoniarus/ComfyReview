import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftPreview } from "../../static/js/playground/draft-preview.js";
import {
  DualRangeControl,
  orderedRange,
} from "../../static/js/playground/dual-range-control.js";
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
    editor.applyIntent({ componentUids: ["scene-a"] });
    expect(rows[1].querySelector("select")?.value).toBe("fixed");

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
    rows[1].querySelectorAll("select")[1].dispatchEvent(new Event("change"));
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
      loras: [],
    });
    controls.applyIntent({
      checkpoint: "model.safetensors",
      sampler: "euler",
      scheduler: "normal",
      seedMode: "fixed",
      seed: 99,
      steps_min: 18,
      steps_max: 30,
      cfg_min: 5,
      cfg_max: 7,
      denoise: 0.8,
    });
    expect(controls.value().sampler).toEqual(
      expect.objectContaining({
        seed: 99,
        steps: 18,
        steps_max: 30,
        cfg: 5,
        cfg_max: 7,
        denoise: 0.8,
      }),
    );
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

  it("synchronizes accessible dual range inputs and clamps values", () => {
    expect(orderedRange(12, 4, { minimum: 0, maximum: 10, step: 0.5 })).toEqual(
      { lower: 4, upper: 10 },
    );
    expect(
      orderedRange(Number.NaN, 2.24, {
        minimum: 1,
        maximum: 10,
        step: 0.5,
      }),
    ).toEqual({ lower: 1, upper: 2 });

    const range = new DualRangeControl({
      label: "Test",
      minimum: 0,
      maximum: 10,
      step: 1,
      lower: 2,
      upper: 8,
      lowerName: "lower",
      upperName: "upper",
    });
    document.body.append(range.element);
    range.lowerRange.value = "9";
    range.lowerRange.dispatchEvent(new Event("input"));
    expect(range.value()).toEqual({ lower: 8, upper: 9 });
    range.upperNumber.value = "3";
    range.upperNumber.dispatchEvent(new Event("input"));
    expect(range.value()).toEqual({ lower: 3, upper: 8 });
    range.setDisabled(true);
    expect(range.lowerNumber.disabled).toBe(true);
    range.dispose();
  });

  it("applies active generation profiles and preserves ordered LoRAs", () => {
    const root = document.createElement("div");
    const controls = new GenerationControls(root);
    controls.render({
      checkpoints: ["model-a.safetensors", "model-b.safetensors"],
      samplers: ["euler", "dpmpp_2m"],
      schedulers: ["normal", "karras"],
      loras: ["style.safetensors"],
      defaults: {
        checkpoint: "model-a.safetensors",
        seed: 7,
        steps: 20,
        cfg: 5,
        sampler: "euler",
        scheduler: "normal",
        denoise: 1,
      },
      profiles: [
        generationProfile({ archived: true }),
        generationProfile({
          profile_uid: "profile-active",
          is_default: true,
        }),
      ],
    });

    expect(controls.value()).toEqual(
      expect.objectContaining({
        checkpoint: "model-b.safetensors",
        loras: [
          {
            name: "style.safetensors",
            model_strength: 0.8,
            clip_strength: 0.6,
          },
        ],
        sampler: expect.objectContaining({
          seed: 42,
          steps: 24,
          steps_max: 36,
          cfg: 4.5,
          cfg_max: 7,
          randomize_seed: false,
        }),
      }),
    );
    controls.applyIntent({
      generationProfileUid: "profile-active",
      steps_min: "invalid",
      cfg_max: 8,
    });
    expect(controls.value().sampler).toEqual(
      expect.objectContaining({ steps: 24, cfg_max: 8 }),
    );
    const profile = root.querySelector('[data-field="profile_uid"]');
    profile.value = "";
    profile.dispatchEvent(new Event("change"));
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
        loras: [{ name: "style.safetensors" }],
      }),
    ).toEqual(
      expect.objectContaining({
        draft_uid: "draft-1",
        component_uids: components.map((item) => item.component_uid),
        positive_atoms: [{ text: "edited", weight: 1 }],
        loras: [{ name: "style.safetensors" }],
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
    const navigator = { open: vi.fn() };
    const view = new TopCombinationsView(root, navigator);

    view.render({
      two_component: [
        {
          label: "Aiko + Rooftop",
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
          component_uids: ["character-a", "scene-a"],
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
    root.querySelector("[data-playground-intent]")?.click();
    expect(navigator.open).toHaveBeenCalled();
    root
      .appendChild(document.createTextNode("plain"))
      .dispatchEvent(new Event("click", { bubbles: true }));

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

function generationProfile(overrides = {}) {
  return {
    profile_uid: "profile-a",
    name: "Editorial",
    checkpoint: "model-b.safetensors",
    sampler: "dpmpp_2m",
    scheduler: "karras",
    seed_mode: "fixed",
    fixed_seed: 42,
    steps_min: 24,
    steps_max: 36,
    cfg_min: 4.5,
    cfg_max: 7,
    denoise: 0.9,
    batch_size: 2,
    loras: [
      {
        name: "style.safetensors",
        model_strength: 0.8,
        clip_strength: 0.6,
      },
    ],
    archived: false,
    is_default: false,
    ...overrides,
  };
}
