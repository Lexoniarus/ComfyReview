/** Own one accessible ordered numeric range with range and number inputs. */
export class DualRangeControl {
  /** @param {{label: string, minimum: number, maximum: number, step: number, lower: number, upper: number, lowerName: string, upperName: string}} options */
  constructor(options) {
    this.options = options;
    this.abortController = new AbortController();
    this.element = document.createElement("fieldset");
    this.element.className = "dual-range-control";
    const legend = document.createElement("legend");
    legend.textContent = options.label;
    this.lowerRange = rangeInput(options, options.lowerName, options.lower);
    this.upperRange = rangeInput(options, options.upperName, options.upper);
    this.lowerNumber = numberInput(options, options.lowerName, options.lower);
    this.upperNumber = numberInput(options, options.upperName, options.upper);
    const track = document.createElement("div");
    track.className = "dual-range-track";
    track.append(this.lowerRange, this.upperRange);
    const values = document.createElement("div");
    values.className = "dual-range-values";
    values.append(
      labeledValue("Von", this.lowerNumber),
      labeledValue("Bis", this.upperNumber),
    );
    this.element.append(legend, track, values);
    this.#bind(this.lowerRange, "lower");
    this.#bind(this.upperRange, "upper");
    this.#bind(this.lowerNumber, "lower");
    this.#bind(this.upperNumber, "upper");
    this.set(options.lower, options.upper);
  }

  /** @returns {{lower: number, upper: number}} */
  value() {
    return {
      lower: Number(this.lowerNumber.value),
      upper: Number(this.upperNumber.value),
    };
  }

  /** @param {number} lower @param {number} upper */
  set(lower, upper) {
    const ordered = orderedRange(lower, upper, this.options);
    this.lowerRange.value = String(ordered.lower);
    this.lowerNumber.value = String(ordered.lower);
    this.upperRange.value = String(ordered.upper);
    this.upperNumber.value = String(ordered.upper);
  }

  /** @param {boolean} disabled */
  setDisabled(disabled) {
    for (const control of [
      this.lowerRange,
      this.upperRange,
      this.lowerNumber,
      this.upperNumber,
    ]) {
      control.disabled = disabled;
    }
  }

  /** Release the owned listeners. */
  dispose() {
    this.abortController.abort();
  }

  /** @param {HTMLInputElement} control @param {"lower" | "upper"} side */
  #bind(control, side) {
    control.addEventListener(
      "input",
      () => {
        const current = this.value();
        const next = Number(control.value);
        this.set(
          side === "lower" ? next : current.lower,
          side === "upper" ? next : current.upper,
        );
      },
      { signal: this.abortController.signal },
    );
  }
}

/** @param {number} lower @param {number} upper @param {{minimum: number, maximum: number, step: number}} limits */
export function orderedRange(lower, upper, limits) {
  const normalizedLower = snap(lower, limits);
  const normalizedUpper = snap(upper, limits);
  return normalizedLower <= normalizedUpper
    ? { lower: normalizedLower, upper: normalizedUpper }
    : { lower: normalizedUpper, upper: normalizedLower };
}

/** @param {number} value @param {{minimum: number, maximum: number, step: number}} limits */
function snap(value, limits) {
  const finite = Number.isFinite(value) ? value : limits.minimum;
  const clamped = Math.min(limits.maximum, Math.max(limits.minimum, finite));
  const steps = Math.round((clamped - limits.minimum) / limits.step);
  return Number((limits.minimum + steps * limits.step).toFixed(6));
}

/** @param {{minimum: number, maximum: number, step: number}} options @param {string} name @param {number} value */
function rangeInput(options, name, value) {
  const control = document.createElement("input");
  control.type = "range";
  configureInput(control, options, name, value);
  return control;
}

/** @param {{minimum: number, maximum: number, step: number}} options @param {string} name @param {number} value */
function numberInput(options, name, value) {
  const control = document.createElement("input");
  control.type = "number";
  configureInput(control, options, name, value);
  return control;
}

/** @param {HTMLInputElement} control @param {{minimum: number, maximum: number, step: number}} options @param {string} name @param {number} value */
function configureInput(control, options, name, value) {
  control.min = String(options.minimum);
  control.max = String(options.maximum);
  control.step = String(options.step);
  control.value = String(value);
  control.dataset.field = name;
}

/** @param {string} label @param {HTMLInputElement} control */
function labeledValue(label, control) {
  const wrapper = document.createElement("label");
  wrapper.append(document.createTextNode(label), control);
  return wrapper;
}
