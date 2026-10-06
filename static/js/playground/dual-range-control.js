/** Own one accessible numeric range with two handles on one track. */
export class DualRangeControl {
  /** @param {{label: string, minimum: number, maximum: number, step: number, lower: number, upper: number, lowerName: string, upperName: string, onChange?: (value: {lower: number, upper: number}) => void}} options */
  constructor(options) {
    this.options = options;
    this.onChange = options.onChange || (() => {});
    this.current = { lower: options.lower, upper: options.upper };
    this.abortController = new AbortController();
    this.element = document.createElement("fieldset");
    this.element.className = "dual-range-control";
    const legend = document.createElement("legend");
    legend.textContent = options.label;
    this.output = document.createElement("output");
    this.output.className = "dual-range-value";
    this.output.setAttribute("aria-live", "polite");
    this.lowerRange = rangeInput(options, options.lowerName, options.lower);
    this.upperRange = rangeInput(options, options.upperName, options.upper);
    this.lowerRange.setAttribute("aria-label", `${options.label}: von`);
    this.upperRange.setAttribute("aria-label", `${options.label}: bis`);
    const track = document.createElement("div");
    track.className = "dual-range-track";
    this.evidence = document.createElement("span");
    this.evidence.className = "dual-range-evidence";
    this.evidence.setAttribute("aria-hidden", "true");
    this.selection = document.createElement("span");
    this.selection.className = "dual-range-selection";
    this.selection.setAttribute("aria-hidden", "true");
    track.append(
      this.evidence,
      this.selection,
      this.lowerRange,
      this.upperRange,
    );
    this.element.append(legend, this.output, track);
    this.#bind(this.lowerRange, "lower");
    this.#bind(this.upperRange, "upper");
    this.set(options.lower, options.upper);
  }

  /** @returns {{lower: number, upper: number}} */
  value() {
    return { ...this.current };
  }

  /** @param {number} lower @param {number} upper */
  set(lower, upper) {
    const ordered = orderedRange(lower, upper, this.options);
    this.lowerRange.value = String(ordered.lower);
    this.upperRange.value = String(ordered.upper);
    this.current = ordered;
    this.#render(ordered);
  }

  /** @param {boolean} disabled */
  setDisabled(disabled) {
    this.lowerRange.disabled = disabled;
    this.upperRange.disabled = disabled;
  }

  /** @param {Array<Record<string, any>>} values @param {"observed" | "predicted"} basis @param {unknown} observedBest @param {unknown} predictedBest */
  setEvidence(values, basis, observedBest, predictedBest) {
    this.evidence.replaceChildren();
    for (const item of values) {
      const score = item?.[basis];
      const numeric = Number(item?.value);
      if (!score || !Number.isFinite(numeric)) continue;
      const segment = document.createElement("i");
      segment.className = "dual-range-evidence-segment";
      segment.style.left = `${this.#position(numeric)}%`;
      segment.dataset.tone = tone(score.relative_rank);
      segment.dataset.source = basis;
      segment.title = `${numeric}: ${(Number(score.expected_success_rate) * 100).toFixed(1)} % · ${Number(score.image_count || 0)} Bilder`;
      this.evidence.append(segment);
    }
    /** @type {Array<["observed" | "predicted", unknown]>} */
    const markers = [
      ["observed", observedBest],
      ["predicted", predictedBest],
    ];
    for (const [source, value] of markers) {
      const numeric = Number(value);
      if (!Number.isFinite(numeric)) continue;
      const marker = document.createElement("b");
      marker.className = "dual-range-guidance-marker";
      marker.dataset.source = source;
      marker.style.left = `${this.#position(numeric)}%`;
      marker.title =
        source === "observed"
          ? "Bestes gesichtetes Ergebnis"
          : "Rechnerische Empfehlung";
      this.evidence.append(marker);
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
        const previous = this.current;
        const next = Number(control.value);
        const ordered = orderedRange(
          side === "lower" ? next : previous.lower,
          side === "upper" ? next : previous.upper,
          this.options,
        );
        this.lowerRange.value = String(ordered.lower);
        this.upperRange.value = String(ordered.upper);
        this.current = ordered;
        this.#render(ordered);
        this.onChange(ordered);
      },
      { signal: this.abortController.signal },
    );
  }

  /** @param {{lower: number, upper: number}} value */
  #render(value) {
    const span = this.options.maximum - this.options.minimum || 1;
    const start = ((value.lower - this.options.minimum) / span) * 100;
    const end = ((value.upper - this.options.minimum) / span) * 100;
    this.element.style.setProperty("--range-start", `${start}%`);
    this.element.style.setProperty("--range-end", `${end}%`);
    this.output.value = formatRange(value);
    this.lowerRange.setAttribute("aria-valuetext", String(value.lower));
    this.upperRange.setAttribute("aria-valuetext", String(value.upper));
  }

  /** @param {number} value */
  #position(value) {
    const span = this.options.maximum - this.options.minimum || 1;
    return Math.min(
      100,
      Math.max(0, ((value - this.options.minimum) / span) * 100),
    );
  }
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

/** @param {number} lower @param {number} upper @param {{minimum: number, maximum: number, step: number}} limits */
export function orderedRange(lower, upper, limits) {
  const normalizedLower = snap(lower, limits);
  const normalizedUpper = snap(upper, limits);
  return normalizedLower <= normalizedUpper
    ? { lower: normalizedLower, upper: normalizedUpper }
    : { lower: normalizedUpper, upper: normalizedLower };
}

/** @param {{lower: number, upper: number}} value */
function formatRange(value) {
  return value.lower === value.upper
    ? String(value.lower)
    : `${value.lower} – ${value.upper}`;
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
  control.min = String(options.minimum);
  control.max = String(options.maximum);
  control.step = String(options.step);
  control.value = String(value);
  control.dataset.field = name;
  return control;
}
