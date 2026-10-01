/** Own technical generation fields populated from blueprint defaults. */
export class GenerationControls {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    /** @type {Map<string, HTMLInputElement | HTMLSelectElement>} */
    this.fields = new Map();
  }

  /** @param {Record<string, any>} capabilities */
  render(capabilities) {
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
    const numbers = document.createElement("div");
    numbers.className = "generation-number-grid";
    numbers.append(
      this.#number("seed", "Seed", defaults.seed, "1"),
      this.#number("steps", "Steps", defaults.steps, "1"),
      this.#number("cfg", "CFG", defaults.cfg, "0.1"),
      this.#number("denoise", "Denoise", defaults.denoise, "0.01"),
    );
    this.root.append(numbers);
  }

  /** Return one typed API sampler configuration. */
  value() {
    return {
      checkpoint: this.#text("checkpoint"),
      sampler: {
        seed: this.#integer("seed"),
        steps: this.#integer("steps"),
        cfg: this.#numberValue("cfg"),
        sampler: this.#text("sampler"),
        scheduler: this.#text("scheduler"),
        denoise: this.#numberValue("denoise"),
      },
    };
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const field of this.fields.values()) field.disabled = busy;
  }

  /** Clear retained field references. */
  dispose() {
    this.fields.clear();
  }

  /** @param {string} name @param {string} label @param {unknown} values @param {unknown} selected */
  #select(name, label, values, selected) {
    const wrapper = field(label);
    const control = document.createElement("select");
    control.dataset.field = name;
    for (const value of Array.isArray(values) ? values : []) {
      control.append(option(String(value)));
    }
    control.value = String(selected || control.value);
    wrapper.append(control);
    this.fields.set(name, control);
    this.root.append(wrapper);
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
function option(value) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = value;
  return element;
}
