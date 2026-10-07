import { beforeEach, describe, expect, it, vi } from "vitest";

import { GenerationProfileEditor } from "../../static/js/settings/generation-profile-editor.js";
import { LoraStackEditor } from "../../static/js/settings/lora-stack-editor.js";
import { SettingsView } from "../../static/js/settings/settings-view.js";

describe("Settings components", () => {
  beforeEach(() => document.body.replaceChildren());

  it("owns ordered LoRA editing and disposal", () => {
    const root = document.createElement("div");
    const editor = new LoraStackEditor(root);
    editor.render(
      [
        { name: "detail.safetensors", model_strength: 0.8, clip_strength: 0.7 },
        { name: "style.safetensors", model_strength: 1, clip_strength: 1 },
      ],
      ["detail.safetensors", "style.safetensors", "light.safetensors"],
    );

    root.querySelectorAll("select")[0].value = "light.safetensors";
    root.querySelectorAll("select")[0].dispatchEvent(new Event("change"));
    root.querySelectorAll("input")[0].value = "0.55";
    root.querySelectorAll("input")[0].dispatchEvent(new Event("input"));
    root.querySelectorAll("input")[1].value = "0.65";
    root.querySelectorAll("input")[1].dispatchEvent(new Event("input"));
    buttonWithText(root, "↓").click();

    expect(editor.value()).toEqual([
      {
        name: "style.safetensors",
        model_strength: 1,
        clip_strength: 1,
        lora_uid: null,
        revision_uid: null,
      },
      {
        name: "light.safetensors",
        model_strength: 0.55,
        clip_strength: 0.65,
        lora_uid: null,
        revision_uid: null,
      },
    ]);
    buttonWithText(root, "LoRA hinzufügen").click();
    expect(editor.value()).toHaveLength(3);
    root
      .querySelectorAll(".settings-lora-row")[2]
      .querySelectorAll("button")[0]
      .click();
    root
      .querySelectorAll(".settings-lora-row")[1]
      .querySelectorAll("button")[2]
      .click();
    expect(editor.value()).toHaveLength(2);
    editor.render(
      [
        { name: "detail.safetensors" },
        { name: "style.safetensors" },
        { name: "light.safetensors" },
      ],
      ["detail.safetensors", "style.safetensors", "light.safetensors"],
    );
    buttonWithText(root, "LoRA hinzufügen").click();
    expect(editor.value()).toHaveLength(3);
    editor.render([{ name: "missing.safetensors" }], ["detail.safetensors"]);
    expect(root.textContent).toContain("Provider-Datei nicht verfügbar");
    expect(root.querySelector(".settings-lora-row").dataset.availability).toBe(
      "missing",
    );
    editor.dispose();
    expect(root.childElementCount).toBe(0);
  });

  it("creates and updates generation profiles through focused actions", () => {
    const root = document.createElement("div");
    const actions = {
      onSave: vi.fn(),
      onArchive: vi.fn(),
      onDefault: vi.fn(),
    };
    const editor = new GenerationProfileEditor(root, actions);
    editor.render(null, capabilities());
    const resolution = root.querySelectorAll("select")[4];
    resolution.value = "768x1152";
    resolution.dispatchEvent(new Event("change"));
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onSave).toHaveBeenCalledWith(
      null,
      expect.objectContaining({
        blueprint_version: 4,
        checkpoint: "model-a.safetensors",
        fixed_seed: null,
        image_width: 768,
        image_height: 1152,
        output_tier: "full_hd_1080",
      }),
    );

    editor.render(
      profile({ archived: false, is_default: false }),
      capabilities(),
    );
    buttonWithText(root, "Archivieren").click();
    buttonWithText(root, "Als Standard").click();
    expect(actions.onArchive).toHaveBeenCalledWith("profile-a", true);
    expect(actions.onDefault).toHaveBeenCalledWith("profile-a");

    editor.render(
      profile({ archived: true, is_default: false }),
      capabilities(),
    );
    buttonWithText(root, "Wiederherstellen").click();
    expect(actions.onArchive).toHaveBeenLastCalledWith("profile-a", false);
    editor.dispose();
  });

  it("renders every settings section and emits typed preference actions", () => {
    const root = document.createElement("div");
    const actions = settingsActions();
    const view = new SettingsView(root, actions);
    const data = settingsData();

    view.render("general", data);
    expect(root.textContent).toContain("Komfortabel");
    expect(root.textContent).toContain("Systemvorgabe");
    expect(root.textContent).not.toContain("Standardprofil");
    root.querySelectorAll("select")[0].value = "compact";
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onPreferencesSave).toHaveBeenCalledWith(
      expect.objectContaining({ density: "compact", analytics_page_size: 24 }),
    );

    view.render("review", data);
    root.querySelector("input[type='checkbox']").click();
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onPreferencesSave).toHaveBeenLastCalledWith(
      expect.objectContaining({ review_prioritize_unrated: false }),
    );

    view.render("content", data);
    expect(root.textContent).toContain("Inhaltsstufen");
    expect(root.textContent).toContain("Explicit");
    const loraRows = root.querySelectorAll(".settings-lora-row");
    expect(loraRows[1].textContent).toContain("Nicht eingestuft");
    expect(loraRows[1].dataset.classification).toBe("unclassified");
    expect(root.querySelector("a").getAttribute("href")).toBe("/catalog");
    const contentBoxes = root.querySelectorAll("input[type='checkbox']");
    expect(contentBoxes[0].disabled).toBe(true);
    contentBoxes[1].click();
    expect(contentBoxes[0].disabled).toBe(false);
    contentBoxes[0].click();
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onPreferencesSave).toHaveBeenLastCalledWith(
      expect.objectContaining({ enabled_content_levels: ["sexy"] }),
    );
    expect(contentBoxes[1].disabled).toBe(true);
    expect(loraRows[0].textContent).toContain("sexy");
    expect(root.textContent).not.toContain("Stufe speichern");

    view.render("curation", data);
    root.querySelectorAll("input")[0].value = "favorites, archive";
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onPreferencesSave).toHaveBeenLastCalledWith(
      expect.objectContaining({ curation_set_order: ["favorites", "archive"] }),
    );

    view.render("comfyui", data);
    root.querySelector("button").click();
    expect(actions.onComfyUiCheck).toHaveBeenCalledOnce();
    expect(root.textContent).toContain("Verbunden");
    view.render("comfyui", {
      ...data,
      runtime: { ...data.runtime, connected: false, message: "not_checked" },
    });
    expect(root.textContent).toContain("Noch nicht geprüft");
    view.render("comfyui", {
      ...data,
      runtime: { ...data.runtime, connected: false, message: "cached" },
    });
    expect(root.textContent).toContain("Nicht live geprüft · letzte Erkennung");

    view.render("storage", data);
    expect(root.textContent).toContain("v9");
    expect(root.textContent).toContain("COMFYUI_BASE_URL");
    view.dispose();
  });

  it("does not expose dormant generation profiles", () => {
    const root = document.createElement("div");
    const actions = settingsActions();
    const view = new SettingsView(root, actions);
    view.render("profiles", settingsData());
    expect(root.textContent).not.toContain("Generierungsprofile");
    expect(root.querySelector("[data-profile-editor]")).toBeNull();
    view.dispose();
  });
});

function settingsActions() {
  return {
    onPreferencesSave: vi.fn(),
    onProfileSave: vi.fn(),
    onProfileArchive: vi.fn(),
    onProfileDefault: vi.fn(),
    onComfyUiCheck: vi.fn(),
    onLoraClassify: vi.fn(),
    onLoraPreview: vi.fn(),
    onLoraApply: vi.fn(),
  };
}

function capabilities() {
  return {
    checkpoints: ["model-a.safetensors"],
    samplers: ["euler"],
    schedulers: ["normal"],
    loras: ["detail.safetensors", "unrated.safetensors"],
    lora_definitions: [
      {
        lora_uid: "lora-detail",
        provider_name: "detail.safetensors",
        latest_revision: {
          revision_uid: "revision-detail",
          content_level: "sexy",
        },
        revision: 2,
      },
    ],
  };
}

function profile(overrides = {}) {
  return {
    profile_uid: "profile-a",
    name: "Standardprofil",
    checkpoint: "model-a.safetensors",
    sampler: "euler",
    scheduler: "normal",
    seed_mode: "fixed",
    fixed_seed: 42,
    steps_min: 24,
    steps_max: 32,
    cfg_min: 5,
    cfg_max: 7,
    denoise: 1,
    batch_size: 2,
    image_width: 768,
    image_height: 1152,
    output_tier: "full_hd_1080",
    loras: [],
    ...overrides,
  };
}

function settingsData() {
  return {
    preferences: {
      density: "comfortable",
      motion: "system",
      analytics_page_size: 24,
      default_generation_profile_uid: "profile-a",
      review_prioritize_unrated: true,
      default_curation_set_key: "favorites",
      curation_set_order: ["favorites"],
      enabled_content_levels: ["standard"],
    },
    generation_profiles: [profile({ is_default: true, archived: false })],
    lora_definitions: capabilities().lora_definitions,
    lora_impacts: {
      "lora-detail": {
        revision: 2,
        generation_count: 3,
        image_count: 4,
      },
    },
    curation_set_keys: ["favorites", "archive"],
    runtime: {
      ...capabilities(),
      upscale_models: ["example-upscaler.pth"],
      connected: true,
      configuration: {
        comfyui_base_url: "http://127.0.0.1:8188",
        output_root: "C:/output",
        workflows_directory: "C:/workflows",
        canonical_database_path: "C:/canonical.sqlite3",
        schema_version: 9,
        runtime_mode: "canonical",
        environment_variables: ["COMFYUI_BASE_URL"],
      },
    },
  };
}

function buttonWithText(root, text) {
  const button = [...root.querySelectorAll("button")].find(
    (candidate) => candidate.textContent === text,
  );
  if (!(button instanceof HTMLButtonElement))
    throw new Error(`Missing ${text}`);
  return button;
}
