import { beforeEach, describe, expect, it, vi } from "vitest";

import { DraftPreview } from "../../static/js/playground/draft-preview.js";
import {
  DualRangeControl,
  orderedRange,
} from "../../static/js/playground/dual-range-control.js";
import { GenerationControls } from "../../static/js/playground/generation-controls.js";
import { PromptModeEditor } from "../../static/js/playground/prompt-mode-editor.js";
import { RenderGuidancePanel } from "../../static/js/playground/render-guidance-panel.js";
import { combinationPromptPatch } from "../../static/js/playground/generator-prompt-projector.js";
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

  it("owns complete fixed, random and off prompt-role intent", async () => {
    const root = document.createElement("div");
    const editor = new PromptModeEditor(root);

    const loraDefinitions = [
      {
        lora_uid: "lora-style",
        provider_name: "style.safetensors",
        display_name: "Style",
        latest_revision: {
          revision_uid: "lora-revision-1",
          default_model_strength: 0.8,
          default_clip_strength: 0.6,
        },
      },
    ];
    editor.render(components, loraDefinitions);
    const rows = root.querySelectorAll(".prompt-mode-row");
    expect(rows).toHaveLength(7);
    expect(rows[0].querySelector("select")?.value).toBe("fixed");
    expect(
      editor.applyState({
        selections: [
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-a",
            revision_uid: "revision-character-a-latest",
          },
          {
            kind: "scene",
            mode: "off",
            component_uid: null,
            revision_uid: null,
          },
        ],
        loras: [
          {
            lora_uid: "lora-style",
            revision_uid: "lora-revision-1",
            model_strength: 0.7,
            clip_strength: 0.5,
          },
        ],
      }),
    ).toEqual([]);
    expect(rows[1].querySelector("select")?.value).toBe("off");
    expect(editor.value().loras).toEqual([
      expect.objectContaining({
        name: "style.safetensors",
        lora_uid: "lora-style",
      }),
    ]);
    expect(
      editor.applyState({
        selections: [
          { kind: "character", mode: "off", component_uid: null },
          { kind: "scene", mode: "fixed", component_uid: "missing" },
          { kind: "unknown", mode: "random", component_uid: null },
        ],
        loras: [{ lora_uid: "missing" }],
      }),
    ).toEqual(["character", "scene", "loras"]);
    editor.applyIntent({ componentUids: ["scene-a"] });
    expect(rows[1].querySelector("select")?.value).toBe("fixed");
    editor.applyIntent({
      loras: [
        {
          lora_uid: "lora-style",
          revision_uid: "lora-revision-1",
          provider_name: "style.safetensors",
          model_strength: 0.7,
          clip_strength: 0.5,
        },
      ],
    });
    expect(editor.value().loras).toEqual([
      expect.objectContaining({
        lora_uid: "lora-style",
        revision_uid: "lora-revision-1",
      }),
    ]);
    Array.from(root.querySelectorAll(".prompt-lora-layer button"))
      .find((button) => button.textContent === "Entfernen")
      .click();

    const sceneMode = rows[1].querySelector("select");
    sceneMode.value = "off";
    sceneMode.dispatchEvent(new Event("change"));
    expect(rows[1].querySelectorAll("select")[1].disabled).toBe(true);
    expect(editor.value()).toEqual(
      expect.objectContaining({
        selections: expect.arrayContaining([
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-a",
            revision_uid: "revision-character-a-latest",
          },
          {
            kind: "scene",
            mode: "off",
            component_uid: null,
            revision_uid: null,
          },
        ]),
      }),
    );
    rows[1].querySelectorAll("select")[1].dispatchEvent(new Event("change"));
    editor.dispose();

    const defaultEditor = new PromptModeEditor(
      document.createElement("div"),
      null,
      {
        loadComponent: async () => ({
          name: "Aiko",
          kind: "character",
          top_images: [{ image_url: "/default.png" }],
        }),
      },
    );
    defaultEditor.render(components);
    await settle();
    defaultEditor.root.querySelector(".prompt-reference-image").click();
    defaultEditor.root
      .querySelector("select")
      .dispatchEvent(new Event("change"));
    defaultEditor.onChange();
    defaultEditor.dispose();
  });

  it("keeps a restored historical fixed revision without catalog history", () => {
    const root = document.createElement("div");
    const editor = new PromptModeEditor(root);
    const character = {
      ...component("character-a", "character", "Aiko"),
      latest_revision: { revision_uid: "character-rev-2", revision_number: 2 },
    };

    editor.render([character]);
    expect(
      editor.applyState({
        selections: [
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-a",
            revision_uid: "character-rev-1",
          },
        ],
      }),
    ).toEqual([]);

    expect(
      root.querySelector(".prompt-mode-row select:nth-of-type(2)").value,
    ).toBe("character-a");
    expect(editor.value().selections[0]).toEqual({
      kind: "character",
      mode: "fixed",
      component_uid: "character-a",
      revision_uid: "character-rev-1",
    });

    editor.dispose();
  });

  it("applies a Combination patch with latest revisions and preserves other roles", () => {
    const root = document.createElement("div");
    const editor = new PromptModeEditor(root);
    const catalog = components.map((item) => ({
      ...item,
      latest_revision: {
        revision_uid: `${item.component_uid}-latest`,
        revision_number: 4,
      },
    }));
    editor.render(catalog);
    expect(
      editor.applyState({
        selections: [
          {
            kind: "character",
            mode: "fixed",
            component_uid: "character-a",
            revision_uid: "character-historical",
          },
          {
            kind: "pose",
            mode: "fixed",
            component_uid: "pose-a",
            revision_uid: "pose-historical",
          },
        ],
        loras: [],
      }),
    ).toEqual([]);

    expect(
      editor.applyState(
        combinationPromptPatch([
          { kind: "scene", component_uid: "scene-a" },
          { kind: "outfit", component_uid: "outfit-a" },
        ]),
      ),
    ).toEqual([]);
    expect(editor.value()).toEqual({
      selections: expect.arrayContaining([
        {
          kind: "character",
          mode: "fixed",
          component_uid: "character-a",
          revision_uid: "character-historical",
        },
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: "scene-a-latest",
        },
        {
          kind: "outfit",
          mode: "fixed",
          component_uid: "outfit-a",
          revision_uid: "outfit-a-latest",
        },
        {
          kind: "pose",
          mode: "fixed",
          component_uid: "pose-a",
          revision_uid: "pose-historical",
        },
      ]),
      loras: [],
    });
    editor.dispose();
  });

  it("ignores invalid prompt modes and safely skips stale evidence rows", () => {
    const root = document.createElement("div");
    const editor = new PromptModeEditor(root);
    editor.render(components);
    const sceneRow = root.querySelector('.prompt-mode-row[data-kind="scene"]');
    const mode = sceneRow.querySelector("select");
    const previous = editor.value();
    mode.append(new Option("invalid", "invalid"));
    mode.value = "invalid";
    mode.dispatchEvent(new Event("change"));
    expect(editor.value()).toEqual(previous);

    const originalGet = editor.rows.get.bind(editor.rows);
    let sceneLookups = 0;
    vi.spyOn(editor.rows, "get").mockImplementation((kind) => {
      if (kind === "scene" && ++sceneLookups === 2) return undefined;
      return originalGet(kind);
    });
    mode.value = "off";
    mode.dispatchEvent(new Event("change"));
    expect(editor.value().selections[1].mode).toBe("off");

    editor.dispose();
  });

  it("uses latest after a manual component change or leaving fixed mode", () => {
    const root = document.createElement("div");
    const editor = new PromptModeEditor(root);
    const catalog = [
      {
        ...component("character-a", "character", "Aiko"),
        latest_revision: {
          revision_uid: "character-rev-2",
          revision_number: 2,
        },
      },
      {
        ...component("character-b", "character", "Hina"),
        latest_revision: {
          revision_uid: "character-b-rev-3",
          revision_number: 3,
        },
      },
      {
        ...component("scene-a", "scene", "Rooftop"),
        latest_revision: { revision_uid: "scene-rev-2", revision_number: 2 },
      },
    ];
    editor.render(catalog);
    editor.applyState({
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
          revision_uid: "scene-rev-1",
        },
      ],
    });

    const characterRow = root.querySelector(
      '.prompt-mode-row[data-kind="character"]',
    );
    const characterComponent = characterRow.querySelectorAll("select")[1];
    characterComponent.value = "character-b";
    characterComponent.dispatchEvent(new Event("change"));
    expect(editor.value().selections[0]).toEqual({
      kind: "character",
      mode: "fixed",
      component_uid: "character-b",
      revision_uid: "character-b-rev-3",
    });

    const sceneRow = root.querySelector('.prompt-mode-row[data-kind="scene"]');
    const sceneMode = sceneRow.querySelector("select");
    editor.applyState({
      selections: [
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: null,
        },
      ],
    });
    expect(editor.value().selections[1]).toEqual({
      kind: "scene",
      mode: "fixed",
      component_uid: "scene-a",
      revision_uid: "scene-rev-2",
    });
    sceneMode.value = "random";
    sceneMode.dispatchEvent(new Event("change"));
    expect(editor.value().selections[1]).toEqual({
      kind: "scene",
      mode: "random",
      component_uid: null,
      revision_uid: null,
    });
    sceneMode.value = "fixed";
    sceneMode.dispatchEvent(new Event("change"));
    expect(editor.value().selections[1]).toEqual({
      kind: "scene",
      mode: "fixed",
      component_uid: "scene-a",
      revision_uid: "scene-rev-2",
    });

    editor.applyState({
      selections: [
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: "scene-rev-1",
        },
      ],
    });
    sceneMode.value = "off";
    sceneMode.dispatchEvent(new Event("change"));
    expect(editor.value().selections[1]).toEqual({
      kind: "scene",
      mode: "off",
      component_uid: null,
      revision_uid: null,
    });

    editor.dispose();
  });

  it("loads, caches and resolves prompt reference evidence", async () => {
    const root = document.createElement("div");
    const loadComponent = vi.fn(async (uid) => ({
      component_uid: uid,
      kind: "character",
      name: "Aiko",
      top_images: [
        { image_url: "/aiko.png", average_rating: 9, rating_count: 4 },
      ],
    }));
    const onImageSelect = vi.fn();
    const editor = new PromptModeEditor(root, () => {}, {
      loadComponent,
      onImageSelect,
    });
    editor.render(components);
    await settle();
    expect(root.textContent).toContain("Aiko · character");
    expect(root.textContent).toContain("Wird beim Entwurf ausgewählt");
    root
      .querySelector(".prompt-reference-image")
      ?.dispatchEvent(new Event("click"));
    expect(onImageSelect).toHaveBeenCalledWith("/aiko.png");
    editor.showResolvedComponents([
      { kind: "scene", component_uid: "scene-a" },
    ]);
    await settle();
    expect(loadComponent).toHaveBeenCalledWith(
      "scene-a",
      expect.any(AbortSignal),
    );
    editor.showResolvedComponents([
      { kind: "character", component_uid: "character-a" },
    ]);
    await settle();
    expect(
      loadComponent.mock.calls.filter(([uid]) => uid === "character-a"),
    ).toHaveLength(1);
    editor.dispose();
  });

  it("shows prompt-reference empty/error states and cancels pending requests", async () => {
    const emptyRoot = document.createElement("div");
    const empty = new PromptModeEditor(emptyRoot, () => {}, {
      loadComponent: vi.fn(async () => ({
        component_uid: "character-a",
        kind: "character",
        name: "Aiko",
        top_images: [],
      })),
    });
    empty.render(components);
    await settle();
    expect(emptyRoot.textContent).toContain(
      "Noch kein sichtbares Referenzbild",
    );
    const characterSelect = emptyRoot.querySelectorAll(
      ".prompt-mode-row select",
    )[1];
    characterSelect.dispatchEvent(new Event("change"));
    await settle();
    expect(emptyRoot.textContent).toContain(
      "Noch kein sichtbares Referenzbild",
    );

    const scene = empty.rows.get("scene");
    scene.mode.value = "random";
    empty.showResolvedComponents([{ kind: "scene", component_uid: "" }]);
    empty.rows.set("scene", {
      mode: scene.mode,
      component: scene.component,
      evidence: undefined,
    });
    empty.showResolvedComponents([{ kind: "scene", component_uid: "" }]);
    empty.rows.delete("character");
    emptyRoot
      .querySelector(".prompt-mode-row select")
      .dispatchEvent(new Event("change"));
    empty.dispose();

    const failedRoot = document.createElement("div");
    let rejectPending;
    const failed = new PromptModeEditor(failedRoot, () => {}, {
      loadComponent: vi.fn(
        () =>
          new Promise((resolve, reject) => {
            rejectPending = reject;
          }),
      ),
    });
    failed.render(components);
    rejectPending(new Error("kaputt"));
    await settle();
    expect(failedRoot.textContent).toContain(
      "Referenz konnte nicht geladen werden",
    );
    failed.render(components);
    failed.dispose();
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
      aspect_format: "1:1",
      resolution_class: "1080",
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
    const cfgStep = root.querySelector('[data-field="cfg_step"]');
    expect(cfgStep.closest("label").hidden).toBe(true);
    expect(
      controls.applyState({
        checkpoint: "model.safetensors",
        sampler: "euler",
        scheduler: "normal",
        seed_mode: "random",
        seed: 99,
        steps_min: 18,
        steps_max: 30,
        cfg_min: 5,
        cfg_max: 7,
        cfg_step: 0.25,
        denoise: 0.8,
        batch_runs: 3,
        aspect_format: "16:9",
        resolution_class: "2160",
      }),
    ).toEqual([]);
    expect(controls.stateValue()).toEqual({
      checkpoint: "model.safetensors",
      sampler: "euler",
      scheduler: "normal",
      seed_mode: "random",
      seed: 99,
      steps_min: 18,
      steps_max: 30,
      cfg_min: 5,
      cfg_max: 7,
      cfg_step: 0.25,
      denoise: 0.8,
      batch_runs: 3,
      aspect_format: "16:9",
      resolution_class: "2160",
    });
    expect(
      controls.applyState({
        checkpoint: "missing",
        seed_mode: "unsupported",
        aspect_format: "missing",
      }),
    ).toEqual(["checkpoint", "seed_mode", "aspect_format"]);
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
    expect(controls.applyIntent({ checkpoint: "missing" })).toEqual([
      "checkpoint",
    ]);
    expect(cfgStep.closest("label").hidden).toBe(false);
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
    expect(controls.draftValue().randomize_seed).toBe(true);
    controls.useConcreteSeed(123);
    expect(controls.value().sampler.seed).toBe(123);
    expect(
      controls.applyRenderSettings({
        checkpoint: "model.safetensors",
        sampler: "euler",
        scheduler: "normal",
        steps: 32,
        cfg: 7.5,
        denoise: 0.9,
      }),
    ).toEqual([]);
    expect(controls.steps.value()).toEqual({ lower: 32, upper: 32 });
    expect(controls.cfg.value()).toEqual({ lower: 7.5, upper: 7.5 });
    expect(controls.applyParameter("sampler", "missing")).toBe(false);
    expect(controls.applyParameter("unknown", "value")).toBe(false);
    expect(controls.applyParameter("steps", 28)).toBe(true);
    expect(controls.applyParameter("cfg", 6.2)).toBe(true);
    expect(controls.applyParameter("denoise", 0.75)).toBe(true);
    controls.steps.lowerRange.dispatchEvent(new Event("input"));
    controls.cfg.upperRange.value = "7";
    controls.cfg.upperRange.dispatchEvent(new Event("input"));
    controls.renderGuidance(
      {
        parameter_values: [
          {
            parameter: "sampler",
            value: "euler",
            observed: {
              expected_success_rate: 0.75,
              image_count: 6,
              review_count: 8,
              relative_rank: 1,
            },
          },
          {
            parameter: "steps",
            value: "32",
            observed: {
              expected_success_rate: 0.7,
              image_count: 5,
              review_count: 5,
              relative_rank: 1,
            },
          },
          {
            parameter: "cfg",
            value: "7.5",
            observed: {
              expected_success_rate: 0.7,
              image_count: 5,
              review_count: 5,
              relative_rank: 1,
            },
          },
        ],
        recommendations: {
          observed_parameters: {
            settings: { sampler: "euler", steps: 32, cfg: 7.5 },
          },
          predicted_parameters: { settings: { steps: 30, cfg: 6.5 } },
        },
      },
      "observed",
    );
    expect(
      root.querySelector('[data-guidance-hint="sampler"]')?.textContent,
    ).toContain("6 Bilder");
    expect(controls.steps.evidence.children.length).toBeGreaterThan(0);
    controls.setBusy(true);
    expect(root.querySelector("select")?.disabled).toBe(true);
    controls.setBusy(false);
    expect(seed.disabled).toBe(false);
    controls.dispose();

    const unrendered = new GenerationControls(document.createElement("div"));
    expect(unrendered.applyRenderSettings({})).toEqual([
      "checkpoint",
      "sampler",
      "scheduler",
    ]);
    unrendered.dispose();
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
    range.upperRange.value = "3";
    range.upperRange.dispatchEvent(new Event("input"));
    expect(range.value()).toEqual({ lower: 3, upper: 8 });
    range.setDisabled(true);
    expect(range.lowerRange.disabled).toBe(true);
    expect(range.element.querySelector('input[type="number"]')).toBeNull();
    range.setEvidence(
      [{ value: "invalid", observed: { relative_rank: 0.5 } }, { value: 4 }],
      "observed",
      "invalid",
      null,
    );
    range.dispose();
  });

  it("renders and applies all four guidance modes explicitly", () => {
    const root = document.createElement("section");
    const onApplySetup = vi.fn();
    const onApplyParameter = vi.fn();
    const panel = new RenderGuidancePanel(root, {
      onApplySetup,
      onApplyParameter,
    });
    const recommendation = {
      applicable: true,
      settings: {
        checkpoint: "model",
        sampler: "euler",
        scheduler: "normal",
        steps: 24,
        cfg: 6.5,
        denoise: 1,
      },
      evidence: {
        expected_success_rate: 0.8,
        image_count: 6,
        review_count: 8,
        confidence: "low",
        jointly_observed: true,
        relative_rank: 1,
      },
    };
    panel.render({
      current: { observed: recommendation, predicted: recommendation },
      recommendations: {
        observed_setup: recommendation,
        observed_parameters: recommendation,
        predicted_setup: recommendation,
        predicted_parameters: recommendation,
      },
      parameter_values: Object.entries(recommendation.settings).map(
        ([parameter, value]) => ({
          parameter,
          value: String(value),
          applicable: true,
          observed: recommendation.evidence,
          predicted: recommendation.evidence,
        }),
      ),
    });
    const setupAction = /** @type {HTMLButtonElement} */ (
      root.querySelector("[data-guidance-action='setup']")
    );
    setupAction.click();
    expect(onApplySetup).toHaveBeenCalledWith(recommendation.settings);
    let radios = root.querySelectorAll("input[type='radio']");
    radios[1].checked = true;
    radios[1].dispatchEvent(new Event("change", { bubbles: true }));
    const parameterMode = /** @type {HTMLInputElement} */ (
      root.querySelector('input[name="guidance-scope"][value="parameter"]')
    );
    parameterMode.checked = true;
    parameterMode.dispatchEvent(new Event("change", { bubbles: true }));
    const parameterAction = /** @type {HTMLButtonElement} */ (
      root.querySelector("[data-guidance-action='parameter']")
    );
    expect(parameterAction).toBeInstanceOf(HTMLButtonElement);
    expect(parameterAction.disabled).toBe(false);
    parameterAction.click();
    expect(onApplyParameter).toHaveBeenCalled();
    expect(root.querySelector("[data-source='predicted']")).not.toBeNull();
    panel.dispose();
  });

  it("renders guidance loading, empty, unavailable and neutral states safely", () => {
    const root = document.createElement("section");
    const onApplySetup = vi.fn();
    const onApplyParameter = vi.fn();
    const onModeChange = vi.fn();
    const panel = new RenderGuidancePanel(root, {
      onApplySetup,
      onApplyParameter,
      onModeChange,
    });
    panel.renderLoading();
    expect(root.textContent).toContain("Evidenz wird berechnet");
    panel.renderLoading("Neu laden");
    expect(root.textContent).toContain("Neu laden");
    root.dispatchEvent(new Event("change", { bubbles: true }));
    root.dispatchEvent(new Event("click", { bubbles: true }));

    panel.render({
      current: {},
      recommendations: {
        observed_setup: {
          applicable: false,
          settings: {},
          evidence: {
            expected_success_rate: "invalid",
            image_count: 0,
            review_count: 0,
            confidence: "unknown",
            relative_rank: null,
          },
        },
      },
      parameter_values: null,
    });
    expect(root.textContent).toContain("nicht belastbar bewertbar");
    const setup = root.querySelector("[data-guidance-action='setup']");
    expect(setup.disabled).toBe(true);
    setup.click();
    setup.disabled = false;
    setup.dispatchEvent(new Event("click", { bubbles: true }));
    expect(onApplySetup).not.toHaveBeenCalled();

    const parameterMode = root.querySelector(
      'input[name="guidance-scope"][value="parameter"]',
    );
    parameterMode.checked = true;
    parameterMode.dispatchEvent(new Event("change", { bubbles: true }));
    expect(root.textContent).toContain("keine belastbare Empfehlung");
    expect(onModeChange).toHaveBeenCalledWith("observed", "parameter");
    panel.dispose();

    const defaultPanel = new RenderGuidancePanel(
      document.createElement("section"),
    );
    defaultPanel.render(null);
    const noRecommendation = new RenderGuidancePanel(
      document.createElement("section"),
    );
    noRecommendation.render({ current: {}, recommendations: {} });
    expect(noRecommendation.root.textContent).toContain(
      "keine belastbare Empfehlung",
    );
    noRecommendation.dispose();
    defaultPanel.root.querySelector("[data-guidance-body]").remove();
    defaultPanel.render({ current: {}, recommendations: {} });
    const actionable = new RenderGuidancePanel(
      document.createElement("section"),
    );
    actionable.render({
      current: {},
      recommendations: {
        observed_setup: {
          applicable: true,
          settings: {},
          evidence: {},
        },
        observed_parameters: {
          applicable: true,
          settings: { checkpoint: "model" },
          evidence: {},
        },
      },
      parameter_values: [],
    });
    actionable.root.querySelector("[data-guidance-action='setup']").click();
    const actionableParameter = actionable.root.querySelector(
      'input[name="guidance-scope"][value="parameter"]',
    );
    actionableParameter.checked = true;
    actionableParameter.dispatchEvent(new Event("change", { bubbles: true }));
    actionable.root.querySelector("[data-guidance-action='parameter']").click();
    actionable.dispose();
    defaultPanel.dispose();
  });

  it("ignores dormant profiles and keeps direct generator defaults", () => {
    const root = document.createElement("div");
    const controls = new GenerationControls(root);
    controls.render({
      checkpoints: ["model-a.safetensors", "model-b.safetensors"],
      samplers: ["euler", "dpmpp_2m"],
      schedulers: ["normal", "karras"],
      loras: ["style.safetensors"],
      lora_definitions: [
        {
          lora_uid: "lora-style",
          provider_name: "style.safetensors",
          content_level: "lewd",
        },
      ],
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
          image_width: 832,
          image_height: 1216,
        }),
      ],
    });

    expect(root.querySelector('[data-field="profile_uid"]')).toBeNull();
    expect(controls.value()).toEqual(
      expect.objectContaining({
        checkpoint: "model-a.safetensors",
        aspect_format: "1:1",
        resolution_class: "1080",
      }),
    );
    controls.applyIntent({
      steps_min: "invalid",
      cfg_max: 8,
    });
    expect(controls.value().sampler).toEqual(
      expect.objectContaining({ steps: 20, cfg_max: 8 }),
    );
    controls.dispose();
  });

  it("falls back to a real capability when a blueprint default is stale", () => {
    const root = document.createElement("div");
    const controls = new GenerationControls(root);
    controls.render({
      checkpoints: ["available.safetensors"],
      samplers: ["euler"],
      schedulers: ["normal"],
      defaults: {
        checkpoint: "missing.safetensors",
        sampler: "missing",
        scheduler: "missing",
      },
    });

    expect(controls.draftValue()).toEqual(
      expect.objectContaining({
        checkpoint: "available.safetensors",
        sampler: "euler",
        scheduler: "normal",
      }),
    );
    controls.dispose();
  });

  it("keeps edits as draft overrides and builds the UID-based payload", () => {
    const root = document.createElement("div");
    const state = document.createElement("span");
    const onChange = vi.fn();
    const onImageSelect = vi.fn();
    const preview = new DraftPreview(root, state, onChange, onImageSelect);
    expect(preview.generationPayload({})).toBeNull();
    expect(preview.promptPayload()).toBeNull();

    preview.render(
      {
        components,
        positive_prompt: "positive",
        negative_prompt: "negative",
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [{ text: "negative", weight: 1 }],
        groups: [
          {
            component_uid: "character-a",
            kind: "character",
            name: "Aiko",
            positive_atoms: [{ text: "positive", weight: 1 }],
            negative_atoms: [{ text: "negative", weight: 1 }],
          },
        ],
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
    preview.renderEvidence({
      prompt_match: {
        image_uid: "shared-image",
        image_url: "/image/shared",
        average_rating: 9,
        rating_count: 4,
      },
      sampler_match: {
        image_uid: "shared-image",
        image_url: "/image/shared",
        average_rating: 9,
        rating_count: 4,
      },
    });
    expect(root.querySelectorAll(".draft-evidence-card")).toHaveLength(1);
    expect(root.textContent).toContain("Prompt-ähnlich · Sampler-ähnlich");
    expect(root.querySelector(".draft-evidence-card img")?.alt).toContain(
      "Prompt-ähnlich",
    );
    preview.renderEvidence({ prompt_match: null, sampler_match: null });
    expect(root.textContent).toContain("Noch kein passender Bildtreffer");
    preview.renderEvidence({
      prompt_matches: [
        { image_uid: "prompt-only", image_url: "/prompt.png" },
        { image_url: "/ignored.png" },
      ],
      sampler_matches: [
        { image_uid: "sampler-only", image_url: "/sampler.png" },
      ],
    });
    expect(root.querySelectorAll(".draft-evidence-carousel")).toHaveLength(2);
    root.querySelector(".evidence-carousel-image").click();
    expect(onImageSelect).toHaveBeenCalledWith("/prompt.png");

    expect(
      preview.generationPayload({
        checkpoint: "model.safetensors",
        aspect_format: "2:3",
        resolution_class: "1080",
        sampler: { seed: 1 },
        loras: [{ name: "style.safetensors" }],
      }),
    ).toEqual(
      expect.objectContaining({
        draft_uid: "draft-1",
        component_uids: components.map((item) => item.component_uid),
        positive_atoms: [{ text: "edited", weight: 1 }],
        loras: [
          {
            name: "style.safetensors",
            lora_uid: null,
            revision_uid: null,
            model_strength: 1,
            clip_strength: 1,
          },
        ],
      }),
    );

    preview.render(
      {
        components: [component("scene-a", "scene", "Scene")],
        positive_prompt: "positive",
        negative_prompt: "negative",
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [{ text: "negative", weight: 1 }],
        groups: [],
        draft_overridden: true,
      },
      "draft-2",
    );
    expect(preview.generationPayload({})).toBeNull();
    preview.dispose();

    const defaultImageRoot = document.createElement("div");
    const defaultState = document.createElement("span");
    const defaultImagePreview = new DraftPreview(
      defaultImageRoot,
      defaultState,
    );
    defaultImagePreview.render(
      {
        components: [component("character-default", "character", "Default")],
        groups: [
          {
            component_uid: "character-default",
            kind: "character",
            name: "Default",
            positive_atoms: [{ text: "tag", weight: 1 }],
            negative_atoms: [],
          },
        ],
      },
      "draft-default",
    );
    defaultImageRoot
      .querySelector("[data-atom-text]")
      .dispatchEvent(new Event("input"));
    defaultImagePreview.renderEvidence({
      prompt_match: {
        image_uid: "default-image",
        image_url: "/default.png",
      },
    });
    defaultImageRoot.querySelector(".evidence-carousel-image").click();
    defaultImagePreview.evidenceCarousel.onSelect({ image_url: "" });
    defaultImagePreview.dispose();

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
        groups: [
          {
            kind: "character",
            name: "Aiko",
            positive_atoms: [{ text: "positive", weight: 1 }],
            negative_atoms: [],
          },
        ],
      },
      "draft-default",
    );
    defaultRoot
      .querySelector("[data-atom-text]")
      .dispatchEvent(new Event("input"));
    defaultPreview.dispose();

    const sceneOnly = new DraftPreview(
      document.createElement("div"),
      document.createElement("span"),
    );
    sceneOnly.render(
      {
        components: [component("scene-a", "scene", "Scene")],
        positive_atoms: [{ text: "scene", weight: 1 }],
        negative_atoms: [],
        groups: [
          {
            kind: "scene",
            name: "Scene",
            positive_atoms: [{ text: "scene", weight: 1 }],
            negative_atoms: [],
          },
        ],
      },
      "draft-scene",
    );
    expect(sceneOnly.generationPayload({})).toBeNull();
    sceneOnly.dispose();
  });

  it("normalizes server draft LoRAs for generation submission", () => {
    const root = document.createElement("div");
    const preview = new DraftPreview(root, document.createElement("span"));
    preview.render(
      {
        components: [component("character-a", "character", "Aiko")],
        positive_atoms: [{ text: "positive", weight: 1 }],
        negative_atoms: [],
        groups: [
          {
            component_uid: "character-a",
            kind: "character",
            name: "Aiko",
            positive_atoms: [{ text: "positive", weight: 1 }],
            negative_atoms: [],
          },
        ],
        loras: [
          {
            lora_uid: "lora-style",
            revision_uid: "lora-revision-1",
            provider_name: "style.safetensors",
            display_name: "Style",
            position: 0,
            model_strength: 0.8,
            clip_strength: 0.6,
          },
        ],
      },
      "draft-lora",
    );

    expect(preview.generationPayload({ sampler: { seed: 1 } }).loras).toEqual([
      {
        name: "style.safetensors",
        lora_uid: "lora-style",
        revision_uid: "lora-revision-1",
        model_strength: 0.8,
        clip_strength: 0.6,
      },
    ]);
    preview.dispose();
  });

  it("renders separate top two- and three-component evidence", () => {
    const root = document.createElement("div");
    const navigator = { open: vi.fn(), openIntent: vi.fn() };
    const view = new TopCombinationsView(root, navigator);

    view.render({
      two_component: [
        {
          label: "Aiko + Rooftop",
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
          component_uids: ["character-a", "scene-a"],
          best_images: [
            { url: "best.png" },
            { url: "second.png" },
            { url: "third.png" },
            { url: "ignored.png" },
          ],
        },
        {
          label: "Hina + Park",
          best_images: [{ url: "" }, { url: "hina.png" }],
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
    expect(root.querySelectorAll("img")).toHaveLength(2);
    expect(root.querySelector("img[src='ignored.png']")).toBeNull();
    const firstCard = root.querySelector(".playground-combination-card");
    expect(firstCard?.getAttribute("data-image-count")).toBe("3");
    firstCard?.querySelector(".evidence-carousel-control.is-next")?.click();
    expect(firstCard?.querySelector("img")?.getAttribute("src")).toBe(
      "second.png",
    );
    const next = root.querySelector("[data-carousel-direction='next']");
    const previous = root.querySelector("[data-carousel-direction='previous']");
    const track = root.querySelector("[data-carousel-track]");
    track?.dispatchEvent(touchEvent("touchend", "changedTouches", 50));
    next?.dispatchEvent(new Event("click", { bubbles: true }));
    expect(track?.getAttribute("data-carousel-index")).toBe("1");
    if (!(track instanceof HTMLElement)) throw new Error("track missing");
    track.scrollTo = vi.fn();
    next?.dispatchEvent(new Event("click", { bubbles: true }));
    next?.dispatchEvent(new Event("click", { bubbles: true }));
    expect(track?.getAttribute("data-carousel-index")).toBe("0");
    expect(track.scrollTo).toHaveBeenCalled();
    previous?.dispatchEvent(new Event("click", { bubbles: true }));
    expect(track?.getAttribute("data-carousel-index")).toBe("2");
    track.dispatchEvent(
      new WheelEvent("wheel", { bubbles: true, deltaX: 40, deltaY: 0 }),
    );
    expect(track?.getAttribute("data-carousel-index")).toBe("0");
    track.dispatchEvent(
      new WheelEvent("wheel", { bubbles: true, deltaX: -40, deltaY: 0 }),
    );
    expect(track?.getAttribute("data-carousel-index")).toBe("2");
    next?.dispatchEvent(new Event("click", { bubbles: true }));
    track.dispatchEvent(
      new WheelEvent("wheel", { bubbles: true, deltaX: 0, deltaY: 40 }),
    );
    expect(track?.getAttribute("data-carousel-index")).toBe("0");
    track.dispatchEvent(touchEvent("touchstart", "touches", 100));
    track.dispatchEvent(touchEvent("touchmove", "touches", 70));
    track.dispatchEvent(touchEvent("touchend", "changedTouches", 50));
    expect(track?.getAttribute("data-carousel-index")).toBe("1");
    track.dispatchEvent(touchEvent("touchstart", "touches", 50));
    track.dispatchEvent(touchEvent("touchmove", "touches", 80));
    track.dispatchEvent(touchEvent("touchend", "changedTouches", 100));
    expect(track?.getAttribute("data-carousel-index")).toBe("0");
    expect(root.querySelectorAll(".playground-character-row")).toHaveLength(1);
    const carouselText = document.createTextNode("carousel plain");
    root.querySelector(".playground-combination-group")?.append(carouselText);
    carouselText.dispatchEvent(new Event("click", { bubbles: true }));
    const legacyAction = document.createElement("button");
    legacyAction.dataset.playgroundIntent = "image";
    root.append(legacyAction);
    legacyAction.click();
    expect(navigator.open).toHaveBeenCalled();
    root
      .appendChild(document.createTextNode("plain"))
      .dispatchEvent(new Event("click", { bubbles: true }));

    view.dispose();
    expect(root.children).toHaveLength(0);
  });

  it("renders independent two- and three-component rows per character", () => {
    const root = document.createElement("div");
    const view = new TopCombinationsView(root, {
      open: vi.fn(),
      openIntent: vi.fn(),
    });

    view.render({
      characters: [
        {
          character_uid: "character-a",
          character_name: "Aiko",
          two_component: [{ label: "Aiko + Rooftop" }],
          three_component: [{ label: "Aiko + Rooftop + Uniform" }],
        },
        {
          character_uid: "character-b",
          character_name: "Hina",
          two_component: [{ label: "Hina + Park" }],
          three_component: [],
        },
      ],
    });

    expect(
      [...root.querySelectorAll(".playground-character-row h3")].map(
        (element) => element.textContent,
      ),
    ).toEqual(["Aiko", "Hina", "Aiko"]);
    expect(root.querySelectorAll("[data-card-rail]")).toHaveLength(3);
    view.dispose();
  });

  it("produces typed kinds only from valid ordered top-combination members", () => {
    const root = document.createElement("div");
    const navigator = { open: vi.fn(), openIntent: vi.fn() };
    const view = new TopCombinationsView(root, navigator);
    view.render({
      characters: [
        {
          character_uid: "character-a",
          character_name: "Aiko",
          two_component: [
            {
              label: "Aiko + Rooftop",
              component_uids: ["character-a", "scene-a"],
            },
          ],
          three_component: [
            {
              label: "Aiko + Rooftop + Uniform",
              component_uids: ["character-a", "scene-a", "outfit-a"],
            },
          ],
        },
      ],
    });

    const actions = root.querySelectorAll(
      ".playground-combination-generator-action",
    );
    expect(actions).toHaveLength(2);
    expect(actions[0].dataset.playgroundIntent).toBeUndefined();
    expect(actions[0].dataset.promptCombination).toBeUndefined();
    const twoComponentIntent = {
      promptCombination: [
        { kind: "character", component_uid: "character-a", revision_uid: null },
        { kind: "scene", component_uid: "scene-a", revision_uid: null },
      ],
    };
    const threeComponentIntent = {
      promptCombination: [
        { kind: "character", component_uid: "character-a", revision_uid: null },
        { kind: "scene", component_uid: "scene-a", revision_uid: null },
        { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
      ],
    };
    actions[0].click();
    actions[1].click();
    expect(navigator.openIntent).toHaveBeenNthCalledWith(1, twoComponentIntent);
    expect(navigator.openIntent).toHaveBeenNthCalledWith(
      2,
      threeComponentIntent,
    );
    expect(navigator.open).not.toHaveBeenCalled();
    view.dispose();
  });

  it("disposes direct Combination button listeners with the view", () => {
    const root = document.createElement("div");
    const navigator = { open: vi.fn(), openIntent: vi.fn() };
    const view = new TopCombinationsView(root, navigator);
    view.render({
      two_component: [{ component_uids: ["character-a", "scene-a"] }],
    });
    const action = root.querySelector(
      ".playground-combination-generator-action",
    );

    view.dispose();
    action.click();

    expect(navigator.openIntent).not.toHaveBeenCalled();
  });

  it("visibly rejects malformed Top Combination source members", () => {
    const root = document.createElement("div");
    const navigator = { open: vi.fn(), openIntent: vi.fn() };
    const view = new TopCombinationsView(root, navigator);
    view.render({
      two_component: [
        { component_uids: ["character-a"] },
        { component_uids: ["character-a", " "] },
      ],
      three_component: [{ component_uids: ["character-a", "scene-a"] }],
    });

    const rejectedActions = root.querySelectorAll(
      ".playground-combination-handoff-error",
    );
    expect(rejectedActions).toHaveLength(3);
    expect(root.textContent).toContain(
      "Generator-Handoff abgewiesen: Erwartet werden exakt 2 Komponenten.",
    );
    expect(root.textContent).toContain(
      "Generator-Handoff abgewiesen: Komponente für scene fehlt.",
    );
    expect(root.querySelector("[data-prompt-combination]")).toBeNull();
    root.querySelectorAll("button").forEach((button) => button.click());
    expect(navigator.openIntent).not.toHaveBeenCalled();
    view.dispose();
  });
});

function component(componentUid, kind, name) {
  return {
    component_uid: componentUid,
    kind,
    name,
    latest_revision: {
      revision_uid: `revision-${componentUid}-latest`,
      revision_number: 1,
    },
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
}

function generationProfile(overrides = {}) {
  return {
    profile_uid: "profile-a",
    name: "Editorial",
    checkpoint: "model-b.safetensors",
    blueprint_uid: "default-character",
    blueprint_version: 4,
    output_tier: "full_hd_1080",
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
    image_width: 768,
    image_height: 1152,
    loras: [
      {
        name: "style.safetensors",
        model_strength: 0.8,
        clip_strength: 0.6,
        lora_uid: "lora-style",
        content_level: "lewd",
      },
    ],
    archived: false,
    is_default: false,
    ...overrides,
  };
}

function touchEvent(type, property, clientX) {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, property, {
    value: [{ clientX, clientY: 0 }],
  });
  return event;
}
