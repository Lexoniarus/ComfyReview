/** Own technical generation fields populated from blueprint defaults. */
export class GenerationControls {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    /** @type {Map<string, HTMLInputElement | HTMLSelectElement>} */
    this.fields = new Map();
    this.abortController = new AbortController();
  }

  /** @param {Record<string, any>} capabilities */
  render(capabilities) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.fields.clear();
    this.root.replaceChildren();
    this.root.className = "generation-controls";
    const defaults = capabilities.defaults || {};
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
      "Seed-Modus",
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
      this.#number("seed", "Seed", defaults.seed, "1"),
      this.#number("steps_min", "Steps von", defaults.steps, "1"),
      this.#number("steps_max", "Steps bis", defaults.steps, "1"),
      this.#number("cfg_min", "CFG von", defaults.cfg, "0.1"),
      this.#number("cfg_max", "CFG bis", defaults.cfg, "0.1"),
      this.#number("cfg_step", "CFG Schritt", 0.1, "0.1"),
      this.#number("denoise", "Denoise", defaults.denoise, "0.01"),
    );
    this.root.append(numbers);
    const seedMode = this.fields.get("seed_mode");
    seedMode?.addEventListener("change", () => this.#syncSeedMode(), {
      signal: this.abortController.signal,
    });
    this.#syncSeedMode();
  }

  /** Return one typed API sampler configuration. */
  value() {
    return {
      checkpoint: this.#text("checkpoint"),
      sampler: {
        seed: this.#integer("seed"),
        steps: this.#integer("steps_min"),
        cfg: this.#numberValue("cfg_min"),
        sampler: this.#text("sampler"),
        scheduler: this.#text("scheduler"),
        denoise: this.#numberValue("denoise"),
        batch_runs: this.#integer("batch_runs"),
        randomize_seed: this.#text("seed_mode") === "random",
        steps_max: this.#integer("steps_max"),
        cfg_max: this.#numberValue("cfg_max"),
        cfg_step: this.#numberValue("cfg_step"),
      },
    };
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const field of this.fields.values()) field.disabled = busy;
    if (!busy) this.#syncSeedMode();
  }

  /** Clear retained field references. */
  dispose() {
    this.abortController.abort();
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

  #syncSeedMode() {
    const seed = this.fields.get("seed");
    if (seed) seed.disabled = this.#text("seed_mode") === "random";
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
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "generation-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}

/** @param {string} value */
function option(value, label = value) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}
