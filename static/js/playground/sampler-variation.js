/** @typedef {{stepsMin: number, stepsMax: number, cfgMin: number, cfgMax: number, cfgStep: number, randomizeSeed: boolean, variantCount: number}} SamplerVariationValue */

/** Own normalized sampler-variation values independently from DOM controls. */
export class SamplerVariation {
  /** @param {Partial<SamplerVariationValue>} [value] */
  constructor(value = {}) {
    this.value = normalizeSamplerVariation(value);
  }

  /** @param {Partial<SamplerVariationValue>} patch */
  update(patch) {
    this.value = normalizeSamplerVariation({ ...this.value, ...patch });
    return this.snapshot();
  }

  /** @returns {SamplerVariationValue} */
  snapshot() {
    return { ...this.value };
  }
}

/** @param {Partial<SamplerVariationValue>} value @returns {SamplerVariationValue} */
export function normalizeSamplerVariation(value) {
  const stepsMin = boundedInteger(value.stepsMin, 1, 100, 24);
  const stepsMax = boundedInteger(value.stepsMax, stepsMin, 100, stepsMin);
  const cfgMin = boundedNumber(value.cfgMin, 0.1, 30, 7);
  const cfgMax = boundedNumber(value.cfgMax, cfgMin, 30, cfgMin);
  return {
    stepsMin,
    stepsMax,
    cfgMin,
    cfgMax,
    cfgStep: boundedNumber(value.cfgStep, 0.01, 30, 0.1),
    randomizeSeed: value.randomizeSeed === true,
    variantCount: boundedInteger(value.variantCount, 1, 12, 1),
  };
}

/** @param {unknown} value @param {number} minimum @param {number} maximum @param {number} fallback */
function boundedInteger(value, minimum, maximum, fallback) {
  const number = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(number)
    ? Math.min(maximum, Math.max(minimum, number))
    : fallback;
}

/** @param {unknown} value @param {number} minimum @param {number} maximum @param {number} fallback */
function boundedNumber(value, minimum, maximum, fallback) {
  const number = Number(value);
  return Number.isFinite(number)
    ? Math.min(maximum, Math.max(minimum, number))
    : fallback;
}
