import { LoraStackEditor } from "./lora-stack-editor.js";

/** Own the focused generation-profile form and its LoRA collaborator. */
export class GenerationProfileEditor {
  /** @param {HTMLElement} root @param {{onSave: (uid: string | null, payload: any) => void, onArchive: (uid: string, archived: boolean) => void, onDefault: (uid: string) => void}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.abortController = new AbortController();
    /** @type {Map<string, HTMLInputElement | HTMLSelectElement>} */
    this.fields = new Map();
    this.loraRoot = document.createElement("div");
    this.loras = new LoraStackEditor(this.loraRoot);
    this.currentUid = null;
  }

  /** @param {Record<string, any> | null} profile @param {Record<string, any>} capabilities */
  render(profile, capabilities) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.fields.clear();
    this.root.replaceChildren();
    this.currentUid = profile?.profile_uid || null;
    const value = profile || newProfile(capabilities);
    const form = document.createElement("form");
    form.className = "settings-form";
    const grid = document.createElement("div");
    grid.className = "settings-profile-grid";
    const resolution = this.#select(
      "resolution_preset",
      "Auflösungsprofil",
      resolutionOptions(),
      resolutionKey(value.image_width, value.image_height),
    );
    grid.append(
      this.#input("name", "Name", value.name),
      this.#select(
        "checkpoint",
        "Checkpoint",
        capabilities.checkpoints,
        value.checkpoint,
      ),
      this.#select("sampler", "Sampler", capabilities.samplers, value.sampler),
      this.#select(
        "scheduler",
        "Scheduler",
        capabilities.schedulers,
        value.scheduler,
      ),
      this.#select(
        "seed_mode",
        "Seedmodus",
        [
          { value: "fixed", label: "Fest" },
          { value: "random", label: "Zufällig" },
        ],
        value.seed_mode,
      ),
      this.#number("fixed_seed", "Fester Seed", value.fixed_seed ?? 1, "1"),
      this.#number("steps_min", "Steps von", value.steps_min, "1"),
      this.#number("steps_max", "Steps bis", value.steps_max, "1"),
      this.#number("cfg_min", "CFG von", value.cfg_min, "0.1"),
      this.#number("cfg_max", "CFG bis", value.cfg_max, "0.1"),
      this.#number("denoise", "Denoise", value.denoise, "0.01"),
      this.#number("batch_size", "Batchgröße", value.batch_size, "1"),
      resolution,
      this.#number("image_width", "Breite", value.image_width, "8"),
      this.#number("image_height", "Höhe", value.image_height, "8"),
    );
    this.fields
      .get("resolution_preset")
      ?.addEventListener("change", () => this.#applyResolutionPreset(), {
        signal: this.abortController.signal,
      });
    this.loras.render(value.loras || [], capabilities.loras || []);
    const actions = document.createElement("div");
    actions.className = "settings-actions";
    const save = actionButton("Speichern");
    save.type = "submit";
    actions.append(save);
    if (this.currentUid) {
      const archive = actionButton(
        value.archived ? "Wiederherstellen" : "Archivieren",
      );
      archive.addEventListener(
        "click",
        () => this.actions.onArchive(this.currentUid, !value.archived),
        { signal: this.abortController.signal },
      );
      actions.append(archive);
      if (!value.archived && !value.is_default) {
        const makeDefault = actionButton("Als Standard");
        makeDefault.addEventListener(
          "click",
          () => this.actions.onDefault(this.currentUid),
          { signal: this.abortController.signal },
        );
        actions.append(makeDefault);
      }
    }
    form.append(grid, this.loraRoot, actions);
    form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        this.actions.onSave(this.currentUid, this.value());
      },
      { signal: this.abortController.signal },
    );
    this.root.append(form);
  }

  /** Return the typed browser profile draft. */
  value() {
    return {
      name: this.#text("name"),
      blueprint_uid: "default-character",
      blueprint_version: 3,
      checkpoint: this.#text("checkpoint"),
      sampler: this.#text("sampler"),
      scheduler: this.#text("scheduler"),
      seed_mode: this.#text("seed_mode"),
      fixed_seed:
        this.#text("seed_mode") === "fixed"
          ? this.#integer("fixed_seed")
          : null,
      steps_min: this.#integer("steps_min"),
      steps_max: this.#integer("steps_max"),
      cfg_min: this.#numberValue("cfg_min"),
      cfg_max: this.#numberValue("cfg_max"),
      denoise: this.#numberValue("denoise"),
      batch_size: this.#integer("batch_size"),
      image_width: this.#integer("image_width"),
      image_height: this.#integer("image_height"),
      loras: this.loras.value(),
    };
  }

  /** Release form and LoRA listeners. */
  dispose() {
    this.abortController.abort();
    this.loras.dispose();
    this.fields.clear();
  }

  /** @param {string} name @param {string} label @param {unknown} value */
  #input(name, label, value) {
    return this.#control(name, label, value, "text", "");
  }

  /** @param {string} name @param {string} label @param {unknown} value @param {string} step */
  #number(name, label, value, step) {
    return this.#control(name, label, value, "number", step);
  }

  /** @param {string} name @param {string} label @param {unknown} value @param {string} type @param {string} step */
  #control(name, label, value, type, step) {
    const wrapper = field(label);
    const control = document.createElement("input");
    control.type = type;
    if (step) control.step = step;
    control.value = String(value ?? "");
    wrapper.append(control);
    this.fields.set(name, control);
    return wrapper;
  }

  /** @param {string} name @param {string} label @param {Array<unknown | {value: unknown, label: string}>} values @param {unknown} selected */
  #select(name, label, values, selected) {
    const wrapper = field(label);
    const control = document.createElement("select");
    for (const item of values || []) {
      const value =
        typeof item === "object" && item !== null && "value" in item
          ? item.value
          : item;
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent =
        typeof item === "object" && item !== null && "label" in item
          ? String(item.label)
          : String(value);
      control.append(option);
    }
    control.value = String(selected || control.value);
    wrapper.append(control);
    this.fields.set(name, control);
    return wrapper;
  }

  /** @param {string} name */
  #text(name) {
    return String(this.fields.get(name)?.value || "");
  }

  /** @param {string} name */
  #integer(name) {
    return Number.parseInt(this.#text(name), 10);
  }

  /** @param {string} name */
  #numberValue(name) {
    return Number.parseFloat(this.#text(name));
  }

  #applyResolutionPreset() {
    const [width, height] = this.#text("resolution_preset")
      .split("x")
      .map(Number);
    if (Number.isInteger(width) && Number.isInteger(height)) {
      const widthField = this.fields.get("image_width");
      const heightField = this.fields.get("image_height");
      if (widthField) widthField.value = String(width);
      if (heightField) heightField.value = String(height);
    }
  }
}

/** @param {Record<string, any>} capabilities */
function newProfile(capabilities) {
  return {
    name: "Neues Profil",
    checkpoint: capabilities.checkpoints?.[0] || "",
    sampler: capabilities.samplers?.[0] || "",
    scheduler: capabilities.schedulers?.[0] || "",
    seed_mode: "random",
    fixed_seed: null,
    steps_min: 24,
    steps_max: 36,
    cfg_min: 4.5,
    cfg_max: 7,
    denoise: 1,
    batch_size: 1,
    image_width: 1024,
    image_height: 1024,
    archived: false,
    is_default: false,
    loras: [],
  };
}

function resolutionOptions() {
  return [
    { value: "1024x1024", label: "Quadrat · 1024 × 1024" },
    { value: "768x1152", label: "Charakterportrait · 768 × 1152" },
    { value: "1280x720", label: "Scene / CG · 1280 × 720" },
    { value: "720x1280", label: "VN-Sprite · 720 × 1280" },
  ];
}

/** @param {number} width @param {number} height */
function resolutionKey(width, height) {
  const key = `${Number(width)}x${Number(height)}`;
  return resolutionOptions().some((option) => option.value === key)
    ? key
    : "1024x1024";
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "settings-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}

/** @param {string} label */
function actionButton(label) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  return button;
}
