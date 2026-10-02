import { LoraStackEditor } from "../settings/lora-stack-editor.js";
import { DualRangeControl } from "./dual-range-control.js";

/** Own technical generation fields populated from profiles and blueprint defaults. */
export class GenerationControls {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    /** @type {Map<string, HTMLInputElement | HTMLSelectElement>} */
    this.fields = new Map();
    /** @type {Array<Record<string, any>>} */
    this.profiles = [];
    /** @type {Record<string, any>} */
    this.capabilities = {};
    /** @type {DualRangeControl | null} */
    this.steps = null;
    /** @type {DualRangeControl | null} */
    this.cfg = null;
    /** @type {LoraStackEditor | null} */
    this.loras = null;
    this.abortController = new AbortController();
  }

  /** @param {Record<string, any>} capabilities */
  render(capabilities) {
    this.#releaseChildren();
    this.abortController.abort();
    this.abortController = new AbortController();
    this.fields.clear();
    this.root.replaceChildren();
    this.root.className = "generation-controls";
    this.capabilities = capabilities;
    this.profiles = Array.isArray(capabilities.profiles)
      ? capabilities.profiles.filter((profile) => !profile.archived)
      : [];
    const defaults = capabilities.defaults || {};
    this.#selectOptions(
      "profile_uid",
      "Generierungsprofil",
      [
        ["", "Blueprint-Defaults"],
        ...this.profiles.map(
          (profile) =>
            /** @type {[string, string]} */ ([
              String(profile.profile_uid),
              String(profile.name),
            ]),
        ),
      ],
      this.profiles.find((profile) => profile.is_default)?.profile_uid || "",
    );
    this.#select(
      "checkpoint",
      "Checkpoint",
      capabilities.checkpoints,
      defaults.checkpoint,
    );
    this.#select("sampler", "Sampler", capabilities.samplers, defaults.sampler);
    this.#select(
      "scheduler",
      "Scheduler",
      capabilities.schedulers,
      defaults.scheduler,
    );
    this.#selectOptions(
      "seed_mode",
      "ComfyUI-Sampler-Seed-Modus",
      [
        ["fixed", "Fest"],
        ["random", "Zufällig"],
      ],
      "fixed",
    );
    const numbers = document.createElement("div");
    numbers.className = "generation-number-grid";
    numbers.append(
      this.#number("batch_runs", "Batch", 1, "1"),
      this.#number("seed", "ComfyUI-Sampler-Seed", defaults.seed, "1"),
      this.#number("cfg_step", "CFG Schritt", 0.1, "0.1"),
      this.#number("denoise", "Denoise", defaults.denoise, "0.01"),
    );
    this.steps = new DualRangeControl({
      label: "Steps-Bereich",
      minimum: 1,
      maximum: 100,
      step: 1,
      lower: Number(defaults.steps ?? 24),
      upper: Number(defaults.steps ?? 24),
      lowerName: "steps_min",
      upperName: "steps_max",
    });
    this.cfg = new DualRangeControl({
      label: "CFG-Bereich",
      minimum: 0,
      maximum: 30,
      step: 0.1,
      lower: Number(defaults.cfg ?? 7),
      upper: Number(defaults.cfg ?? 7),
      lowerName: "cfg_min",
      upperName: "cfg_max",
    });
    const loraRoot = document.createElement("section");
    loraRoot.className = "generation-lora-editor";
    this.loras = new LoraStackEditor(loraRoot);
    this.loras.render([], capabilities.loras || []);
    this.root.append(numbers, this.steps.element, this.cfg.element, loraRoot);
    this.fields
      .get("profile_uid")
      ?.addEventListener("change", () => this.#applySelectedProfile(), {
        signal: this.abortController.signal,
      });
    this.fields
      .get("seed_mode")
      ?.addEventListener("change", () => this.#syncSeedMode(), {
        signal: this.abortController.signal,
      });
    this.#applySelectedProfile();
    this.#syncSeedMode();
  }

  /** Return one typed API sampler and LoRA configuration. */
  value() {
    const steps = this.steps?.value() || { lower: 1, upper: 1 };
    const cfg = this.cfg?.value() || { lower: 0, upper: 0 };
    return {
      checkpoint: this.#text("checkpoint"),
      sampler: {
        seed: this.#integer("seed"),
        steps: steps.lower,
        cfg: cfg.lower,
        sampler: this.#text("sampler"),
        scheduler: this.#text("scheduler"),
        denoise: this.#numberValue("denoise"),
        batch_runs: this.#integer("batch_runs"),
        randomize_seed: this.#text("seed_mode") === "random",
        steps_max: steps.upper,
        cfg_max: cfg.upper,
        cfg_step: this.#numberValue("cfg_step"),
      },
      loras: this.loras?.value() || [],
    };
  }

  /** @param {Record<string, any>} intent */
  applyIntent(intent) {
    if (intent.generationProfileUid) {
      this.#set("profile_uid", intent.generationProfileUid);
      this.#applySelectedProfile();
    }
    for (const [intentName, fieldName] of [
      ["checkpoint", "checkpoint"],
      ["sampler", "sampler"],
      ["scheduler", "scheduler"],
      ["seedMode", "seed_mode"],
      ["seed", "seed"],
      ["denoise", "denoise"],
    ]) {
      const value = intent[intentName];
      if (value !== undefined && value !== null && value !== "") {
        this.#set(fieldName, value);
      }
    }
    const currentSteps = this.steps?.value();
    const currentCfg = this.cfg?.value();
    this.steps?.set(
      numeric(intent.steps_min, currentSteps?.lower ?? 1),
      numeric(intent.steps_max, currentSteps?.upper ?? 1),
    );
    this.cfg?.set(
      numeric(intent.cfg_min, currentCfg?.lower ?? 0),
      numeric(intent.cfg_max, currentCfg?.upper ?? 0),
    );
    this.#syncSeedMode();
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const field of this.fields.values()) field.disabled = busy;
    this.steps?.setDisabled(busy);
    this.cfg?.setDisabled(busy);
    if (!busy) this.#syncSeedMode();
  }

  /** Clear retained field references and child resources. */
  dispose() {
    this.abortController.abort();
    this.#releaseChildren();
    this.fields.clear();
  }

  /** @param {string} name @param {string} label @param {unknown} values @param {unknown} selected */
  #select(name, label, values, selected) {
    this.#selectOptions(
      name,
      label,
      (Array.isArray(values) ? values : []).map((value) => [
        String(value),
        String(value),
      ]),
      selected,
    );
  }

  /** @param {string} name @param {string} label @param {Array<[string, string]>} values @param {unknown} selected */
  #selectOptions(name, label, values, selected) {
    const wrapper = field(label);
    const control = document.createElement("select");
    control.dataset.field = name;
    for (const [value, optionLabel] of values) {
      control.append(option(value, optionLabel));
    }
    control.value = String(selected || control.value);
    wrapper.append(control);
    this.fields.set(name, control);
    this.root.append(wrapper);
  }

  #applySelectedProfile() {
    const profileUid = this.#text("profile_uid");
    const profile = this.profiles.find(
      (candidate) => candidate.profile_uid === profileUid,
    );
    if (!profile) return;
    this.#set("checkpoint", profile.checkpoint);
    this.#set("sampler", profile.sampler);
    this.#set("scheduler", profile.scheduler);
    this.#set("seed_mode", profile.seed_mode);
    if (profile.fixed_seed !== null) this.#set("seed", profile.fixed_seed);
    this.#set("batch_runs", profile.batch_size);
    this.#set("denoise", profile.denoise);
    this.steps?.set(profile.steps_min, profile.steps_max);
    this.cfg?.set(profile.cfg_min, profile.cfg_max);
    this.loras?.render(profile.loras || [], this.capabilities.loras || []);
    this.#syncSeedMode();
  }

  #syncSeedMode() {
    const seed = this.fields.get("seed");
    if (seed) seed.disabled = this.#text("seed_mode") === "random";
  }

  /** @param {string} name @param {unknown} value */
  #set(name, value) {
    const field = this.fields.get(name);
    if (field) field.value = String(value);
  }

  /** @param {string} name @param {string} label @param {unknown} value @param {string} step */
  #number(name, label, value, step) {
    const wrapper = field(label);
    const control = document.createElement("input");
    control.type = "number";
    control.step = step;
    control.value = String(value ?? "");
    control.dataset.field = name;
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

  #releaseChildren() {
    this.steps?.dispose();
    this.cfg?.dispose();
    this.loras?.dispose();
    this.steps = null;
    this.cfg = null;
    this.loras = null;
  }
}

/** @param {unknown} value @param {number} fallback */
function numeric(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "generation-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}

/** @param {string} value @param {string} [label] */
function option(value, label = value) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}
