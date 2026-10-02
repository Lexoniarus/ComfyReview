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
      },
      {
        name: "light.safetensors",
        model_strength: 0.55,
        clip_strength: 0.65,
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
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onSave).toHaveBeenCalledWith(
      null,
      expect.objectContaining({
        blueprint_version: 2,
        checkpoint: "model-a.safetensors",
        fixed_seed: null,
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
      expect.objectContaining({ review_unrated_only: false }),
    );

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

    view.render("storage", data);
    expect(root.textContent).toContain("v8");
    expect(root.textContent).toContain("COMFYUI_BASE_URL");
    view.dispose();
  });

  it("delegates profile selection, creation, persistence and lifecycle", () => {
    const root = document.createElement("div");
    const actions = settingsActions();
    const view = new SettingsView(root, actions);
    view.render("profiles", settingsData());
    expect(root.textContent).toContain("Standard");

    root.querySelectorAll(".settings-profile-list button")[0].click();
    root.querySelectorAll(".settings-profile-list button")[1].click();
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(actions.onProfileSave).toHaveBeenCalledWith(
      null,
      expect.objectContaining({ name: "Neues Profil" }),
    );
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
  };
}

function capabilities() {
  return {
    checkpoints: ["model-a.safetensors"],
    samplers: ["euler"],
    schedulers: ["normal"],
    loras: ["detail.safetensors"],
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
      review_unrated_only: true,
      review_max_attempts: 20,
      default_curation_set_key: "favorites",
      curation_set_order: ["favorites"],
    },
    generation_profiles: [profile({ is_default: true, archived: false })],
    curation_set_keys: ["favorites", "archive"],
    runtime: {
      ...capabilities(),
      connected: true,
      configuration: {
        comfyui_base_url: "http://127.0.0.1:8188",
        output_root: "C:/output",
        workflows_directory: "C:/workflows",
        canonical_database_path: "C:/canonical.sqlite3",
        schema_version: 8,
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
