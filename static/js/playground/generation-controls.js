import { DualRangeControl } from "./dual-range-control.js";
import { SamplerStateAdapter } from "./sampler-state-adapter.js";
import { SamplerVariation } from "./sampler-variation.js";

const renderParameters = [
  "checkpoint",
  "sampler",
  "scheduler",
  "steps",
  "cfg",
  "denoise",
];

/** Own explicit generator values without profile indirection. */
export class GenerationControls {
  /** @param {HTMLElement} root @param {() => void} [onChange] */
  constructor(root, onChange = () => {}) {
    this.root = root;
    this.onChange = onChange;
    /** @type {Map<string, HTMLInputElement | HTMLSelectElement>} */
    this.fields = new Map();
    this.steps = null;
    this.cfg = null;
    this.rangeHints = new Map();
    this.stepsOutput = null;
    this.cfgOutput = null;
    this.abortController = new AbortController();
    this.stateAdapter = new SamplerStateAdapter();
  }

  /** @param {Record<string, any>} capabilities */
  render(capabilities) {
    this.#releaseChildren();
    this.abortController.abort();
    this.abortController = new AbortController();
    this.fields.clear();
    this.rangeHints.clear();
    this.root.replaceChildren();
    this.root.className = "generation-controls";
    const defaults = capabilities.defaults || {};
    const renderGroup = group("Render- und Sampler-Setup");
    this.#select(
      renderGroup.body,
      "checkpoint",
      "Checkpoint",
      capabilities.checkpoints,
      defaults.checkpoint,
    );
    this.#select(
      renderGroup.body,
      "sampler",
      "Sampler",
      capabilities.samplers,
      defaults.sampler,
    );
    this.#select(
      renderGroup.body,
      "scheduler",
      "Scheduler",
      capabilities.schedulers,
      defaults.scheduler,
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
      onChange: () => {
        this.#syncConcreteSummary();
        this.onChange();
      },
    });
    this.cfg = new DualRangeControl({
      label: "CFG-Bereich",
      minimum: 0.1,
      maximum: 30,
      step: 0.1,
      lower: Number(defaults.cfg ?? 7),
      upper: Number(defaults.cfg ?? 7),
      lowerName: "cfg_min",
      upperName: "cfg_max",
      onChange: () => {
        this.#syncCfgStep();
        this.#syncConcreteSummary();
        this.onChange();
      },
    });
    const concrete = document.createElement("div");
    concrete.className = "sampler-concrete-values";
    this.stepsOutput = concreteValue("Steps");
    this.cfgOutput = concreteValue("CFG");
    concrete.append(this.stepsOutput.root, this.cfgOutput.root);
    const variation = document.createElement("details");
    variation.className = "sampler-variation";
    const variationSummary = document.createElement("summary");
    variationSummary.textContent = "Variieren";
    const variationBody = document.createElement("div");
    variationBody.className = "sampler-variation-body";
    variationBody.append(
      this.steps.element,
      this.cfg.element,
      this.#number("cfg_step", "CFG-Schrittweite", 0.1, "0.1"),
    );
    variation.append(variationSummary, variationBody);
    renderGroup.body.append(
      this.#number("denoise", "Denoise", defaults.denoise, "0.01"),
      concrete,
      variation,
    );
    for (const [
      parameter,
      control,
    ] of /** @type {Array<[string, DualRangeControl]>} */ ([
      ["steps", this.steps],
      ["cfg", this.cfg],
    ])) {
      const hint = guidanceHint(parameter);
      control.element.append(hint);
      this.rangeHints.set(parameter, hint);
    }

    const outputGroup = group("Ausgabe");
    this.#selectOptions(
      outputGroup.body,
      "aspect_format",
      "Format / Ausrichtung",
      [
        ["2:3", "2:3 · Hochkant"],
        ["3:2", "3:2 · Querformat"],
        ["16:9", "16:9 · Querformat"],
        ["9:16", "9:16 · Hochkant"],
        ["1:1", "1:1 · Quadrat"],
      ],
      "1:1",
    );
    this.#selectOptions(
      outputGroup.body,
      "resolution_class",
      "Auflösungsklasse",
      [
        ["720", "720p / HD Ready"],
        ["1080", "1080p / Full HD"],
        ["2160", "2160p / 4K"],
      ],
      "1080",
    );

    const runtimeGroup = group("Varianten");
    this.#selectOptions(
      variationBody,
      "seed_mode",
      "Seed variieren",
      [
        ["fixed", "Nein"],
        ["random", "Ja"],
      ],
      "fixed",
    );
    runtimeGroup.body.append(
      this.#number("seed", "Bild-Seed", defaults.seed, "1"),
      this.#number(
        "variant_count",
        "Anzahl Varianten",
        defaults.variant_count ?? 4,
        "1",
      ),
    );
    const variantCount = this.fields.get("variant_count");
    if (variantCount instanceof HTMLInputElement) {
      variantCount.min = "1";
      variantCount.max = "12";
    }
    this.root.append(
      renderGroup.element,
      outputGroup.element,
      runtimeGroup.element,
    );
    for (const control of this.fields.values()) {
      control.addEventListener(
        "change",
        () => {
          this.#syncSeedMode();
          this.#syncCfgStep();
          this.onChange();
        },
        { signal: this.abortController.signal },
      );
    }
    this.#syncSeedMode();
    this.#syncCfgStep();
    this.#syncConcreteSummary();
  }

  /** Return the six optimizer-controlled values. */
  renderSettings() {
    return {
      checkpoint: this.#text("checkpoint"),
      sampler: this.#text("sampler"),
      scheduler: this.#text("scheduler"),
      steps: this.steps?.value().lower ?? 1,
      cfg: this.cfg?.value().lower ?? 1,
      denoise: this.#numberValue("denoise"),
    };
  }

  /** @param {Record<string, any>} payload @param {"observed" | "predicted"} basis */
  renderGuidance(payload, basis) {
    const values = Array.isArray(payload.parameter_values)
      ? payload.parameter_values
      : [];
    /** @type {Record<string, any>} */
    const settings = this.renderSettings();
    const recommendation =
      payload.recommendations?.[`${basis}_parameters`] || null;
    for (const parameter of renderParameters) {
      const current = String(settings[parameter]);
      const item = values.find(
        (candidate) =>
          candidate.parameter === parameter &&
          String(candidate.value) === current,
      );
      const score = item?.[basis] || null;
      const hint =
        parameter === "steps" || parameter === "cfg"
          ? this.rangeHints.get(parameter)
          : this.fields
              .get(parameter)
              ?.closest("label")
              ?.querySelector("[data-guidance-hint]");
      if (hint instanceof HTMLElement) {
        const alternative = recommendation?.settings?.[parameter];
        hint.textContent = score
          ? `${basis === "observed" ? "Gesichtet" : "Rechnerisch"}: ${formatEvidence(score)}${alternative != null ? ` · stärkste Alternative ${alternative}` : ""}`
          : "Noch nicht ausreichend untersucht";
        hint.dataset.source = basis;
        hint.dataset.tone = tone(score?.relative_rank);
      }
      const fieldRoot = this.fields.get(parameter)?.closest("label");
      if (fieldRoot instanceof HTMLElement) {
        fieldRoot.dataset.source = basis;
        fieldRoot.dataset.tone = tone(score?.relative_rank);
      }
    }
    const observed =
      payload.recommendations?.observed_parameters?.settings || {};
    const predicted =
      payload.recommendations?.predicted_parameters?.settings || {};
    this.steps?.setEvidence(
      values.filter((item) => item.parameter === "steps"),
      basis,
      observed.steps,
      predicted.steps,
    );
    this.cfg?.setEvidence(
      values.filter((item) => item.parameter === "cfg"),
      basis,
      observed.cfg,
      predicted.cfg,
    );
  }

  /** @param {Record<string, any>} settings */
  applyRenderSettings(settings) {
    const rejected = [];
    for (const name of ["checkpoint", "sampler", "scheduler"]) {
      if (!this.#setAvailable(name, settings[name])) rejected.push(name);
    }
    if (settings.steps != null)
      this.steps?.set(Number(settings.steps), Number(settings.steps));
    if (settings.cfg != null)
      this.cfg?.set(Number(settings.cfg), Number(settings.cfg));
    if (settings.denoise != null) this.#set("denoise", settings.denoise);
    this.#syncCfgStep();
    this.#syncConcreteSummary();
    this.onChange();
    return rejected;
  }

  /** @param {string} parameter @param {unknown} value */
  applyParameter(parameter, value) {
    if (!renderParameters.includes(parameter)) return false;
    if (parameter === "steps") this.steps?.set(Number(value), Number(value));
    else if (parameter === "cfg") this.cfg?.set(Number(value), Number(value));
    else if (["checkpoint", "sampler", "scheduler"].includes(parameter)) {
      if (!this.#setAvailable(parameter, value)) return false;
    } else this.#set(parameter, value);
    this.#syncCfgStep();
    this.#syncConcreteSummary();
    this.onChange();
    return true;
  }

  /** Return the complete draft settings, including the one shared seed. */
  draftValue() {
    const render = this.renderSettings();
    return {
      ...render,
      seed: this.#text("seed_mode") === "random" ? null : this.#integer("seed"),
      randomize_seed: this.#text("seed_mode") === "random",
      aspect_format: this.#text("aspect_format"),
      resolution_class: this.#text("resolution_class"),
    };
  }

  /** Return reviewed values accepted by generation submission. */
  value() {
    const draft = this.draftValue();
    const variation = this.#variationValue();
    return {
      checkpoint: draft.checkpoint,
      aspect_format: draft.aspect_format,
      resolution_class: draft.resolution_class,
      sampler: {
        seed: this.#integer("seed"),
        steps: variation.stepsMin,
        cfg: variation.cfgMin,
        sampler: draft.sampler,
        scheduler: draft.scheduler,
        denoise: draft.denoise,
        batch_runs: variation.variantCount,
        randomize_seed: false,
        steps_max: variation.stepsMax,
        cfg_max: variation.cfgMax,
        cfg_step: variation.cfgStep,
      },
    };
  }

  /** Return the bounded variant-preparation contract. */
  variantValue() {
    const draft = this.draftValue();
    const variation = this.#variationValue();
    return {
      variant_count: variation.variantCount,
      generation: {
        ...draft,
        steps: variation.stepsMin,
        steps_max: variation.stepsMax,
        cfg: variation.cfgMin,
        cfg_max: variation.cfgMax,
        cfg_step: variation.cfgStep,
      },
    };
  }

  /** Return the complete persistent UI state. */
  stateValue() {
    const value = this.value();
    const sampler = value.sampler;
    return this.stateAdapter.persist({
      checkpoint: value.checkpoint,
      sampler: sampler.sampler,
      scheduler: sampler.scheduler,
      seed_mode: this.#text("seed_mode"),
      seed: sampler.seed,
      steps_min: sampler.steps,
      steps_max: sampler.steps_max,
      cfg_min: sampler.cfg,
      cfg_max: sampler.cfg_max,
      cfg_step: sampler.cfg_step,
      denoise: sampler.denoise,
      variant_count: sampler.batch_runs,
      aspect_format: value.aspect_format,
      resolution_class: value.resolution_class,
    });
  }

  /** Restore saved controls after native capabilities have rendered. @param {Record<string, any>} state */
  applyState(state) {
    state = this.stateAdapter.restore(state);
    const rejected = [];
    for (const name of [
      "checkpoint",
      "sampler",
      "scheduler",
      "seed_mode",
      "aspect_format",
      "resolution_class",
    ]) {
      const value = state[name];
      if (value === undefined || value === null || value === "") continue;
      if (!this.#setAvailable(name, value)) rejected.push(name);
    }
    for (const name of ["seed", "cfg_step", "denoise", "variant_count"]) {
      const value = state[name];
      if (value !== undefined && value !== null && value !== "")
        this.#set(name, value);
    }
    const currentSteps = this.steps?.value();
    const currentCfg = this.cfg?.value();
    this.steps?.set(
      numeric(state.steps_min, currentSteps?.lower ?? 1),
      numeric(state.steps_max, currentSteps?.upper ?? 1),
    );
    this.cfg?.set(
      numeric(state.cfg_min, currentCfg?.lower ?? 1),
      numeric(state.cfg_max, currentCfg?.upper ?? 1),
    );
    this.#syncSeedMode();
    this.#syncCfgStep();
    this.#syncConcreteSummary();
    return rejected;
  }

  /** @param {number} seed */
  useConcreteSeed(seed) {
    this.#set("seed", seed);
    this.#set("seed_mode", "fixed");
    this.#syncSeedMode();
  }

  /** @param {Record<string, any>} intent */
  applyIntent(intent) {
    const rejected = [];
    for (const [intentName, fieldName] of [
      ["checkpoint", "checkpoint"],
      ["sampler", "sampler"],
      ["scheduler", "scheduler"],
      ["seedMode", "seed_mode"],
      ["seed", "seed"],
      ["denoise", "denoise"],
      ["aspectFormat", "aspect_format"],
      ["resolutionClass", "resolution_class"],
    ]) {
      const value = intent[intentName];
      if (value === undefined || value === null || value === "") continue;
      if (["checkpoint", "sampler", "scheduler"].includes(fieldName)) {
        if (!this.#setAvailable(fieldName, value)) rejected.push(fieldName);
      } else {
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
      numeric(intent.cfg_min, currentCfg?.lower ?? 1),
      numeric(intent.cfg_max, currentCfg?.upper ?? 1),
    );
    this.#syncSeedMode();
    this.#syncCfgStep();
    this.#syncConcreteSummary();
    return rejected;
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const field of this.fields.values()) field.disabled = busy;
    this.steps?.setDisabled(busy);
    this.cfg?.setDisabled(busy);
    if (!busy) {
      this.#syncSeedMode();
      this.#syncCfgStep();
    }
  }

  dispose() {
    this.abortController.abort();
    this.#releaseChildren();
    this.fields.clear();
  }

  /** @param {HTMLElement} parent @param {string} name @param {string} label @param {unknown} values @param {unknown} selected */
  #select(parent, name, label, values, selected) {
    this.#selectOptions(
      parent,
      name,
      label,
      (Array.isArray(values) ? values : []).map((value) => [
        String(value),
        String(value),
      ]),
      selected,
    );
  }

  /** @param {HTMLElement} parent @param {string} name @param {string} label @param {Array<[string, string]>} values @param {unknown} selected */
  #selectOptions(parent, name, label, values, selected) {
    const wrapper = field(label);
    const control = document.createElement("select");
    control.dataset.field = name;
    for (const [value, optionLabel] of values)
      control.append(option(value, optionLabel));
    const selectedValue = String(selected || "");
    if (values.some(([value]) => value === selectedValue))
      control.value = selectedValue;
    wrapper.append(control);
    if (renderParameters.includes(name)) wrapper.append(guidanceHint(name));
    this.fields.set(name, control);
    parent.append(wrapper);
  }

  #syncSeedMode() {
    const seed = this.fields.get("seed");
    if (seed) seed.disabled = this.#text("seed_mode") === "random";
  }

  #syncCfgStep() {
    const wrapper = this.fields.get("cfg_step")?.closest("label");
    const cfg = this.cfg?.value();
    if (wrapper instanceof HTMLElement)
      wrapper.hidden = !cfg || cfg.lower === cfg.upper;
  }

  #syncConcreteSummary() {
    const steps = this.steps?.value().lower;
    const cfg = this.cfg?.value().lower;
    if (this.stepsOutput)
      this.stepsOutput.value.textContent = String(steps ?? "—");
    if (this.cfgOutput) this.cfgOutput.value.textContent = String(cfg ?? "—");
  }

  /** @param {string} name @param {unknown} value */
  #set(name, value) {
    const control = this.fields.get(name);
    if (control) control.value = String(value);
  }

  /** @param {string} name @param {unknown} value */
  #setAvailable(name, value) {
    const control = this.fields.get(name);
    if (!(control instanceof HTMLSelectElement)) return false;
    const candidate = String(value ?? "");
    if (![...control.options].some((item) => item.value === candidate))
      return false;
    control.value = candidate;
    return true;
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
    if (renderParameters.includes(name)) wrapper.append(guidanceHint(name));
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

  #variationValue() {
    const steps = this.steps?.value() || { lower: 1, upper: 1 };
    const cfg = this.cfg?.value() || { lower: 1, upper: 1 };
    return new SamplerVariation({
      stepsMin: steps.lower,
      stepsMax: steps.upper,
      cfgMin: cfg.lower,
      cfgMax: cfg.upper,
      cfgStep: this.#numberValue("cfg_step"),
      randomizeSeed: this.#text("seed_mode") === "random",
      variantCount: this.#integer("variant_count"),
    }).snapshot();
  }

  #releaseChildren() {
    this.steps?.dispose();
    this.cfg?.dispose();
    this.steps = null;
    this.cfg = null;
    this.stepsOutput = null;
    this.cfgOutput = null;
  }
}

/** @param {string} label */
function concreteValue(label) {
  const root = document.createElement("span");
  root.className = "sampler-concrete-value";
  const name = document.createElement("small");
  name.textContent = label;
  const value = document.createElement("strong");
  root.append(name, value);
  return { root, value };
}

/** @param {string} title */
function group(title) {
  const element = document.createElement("section");
  element.className = "generation-control-group";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const body = document.createElement("div");
  body.className = "generation-control-group-body";
  element.append(heading, body);
  return { element, body };
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

/** @param {string} parameter */
function guidanceHint(parameter) {
  const hint = document.createElement("small");
  hint.dataset.guidanceHint = parameter;
  hint.className = "generation-guidance-hint";
  return hint;
}

/** @param {Record<string, any>} score */
function formatEvidence(score) {
  return `${(Number(score.expected_success_rate) * 100).toFixed(1)} % · ${Number(score.image_count || 0)} Bilder · ${Number(score.review_count || 0)} Reviews`;
}

/** @param {unknown} value */
function tone(value) {
  const rank = value == null ? Number.NaN : Number(value);
  return Number.isFinite(rank)
    ? rank >= 0.67
      ? "high"
      : rank >= 0.34
        ? "medium"
        : "low"
    : "neutral";
}
