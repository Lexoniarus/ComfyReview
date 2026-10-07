import { describe, expect, it } from "vitest";

import { SamplerStateAdapter } from "../../static/js/playground/sampler-state-adapter.js";
import {
  normalizeSamplerVariation,
  SamplerVariation,
} from "../../static/js/playground/sampler-variation.js";

describe("sampler variation boundaries", () => {
  it("normalizes bounded concrete ranges and variant counts", () => {
    const variation = new SamplerVariation({
      stepsMin: 0,
      stepsMax: 200,
      cfgMin: "invalid",
      cfgMax: 31,
      cfgStep: 0,
      randomizeSeed: true,
      variantCount: 20,
    });

    expect(variation.snapshot()).toEqual({
      stepsMin: 1,
      stepsMax: 100,
      cfgMin: 7,
      cfgMax: 30,
      cfgStep: 0.01,
      randomizeSeed: true,
      variantCount: 12,
    });
    expect(
      variation.update({
        stepsMin: 30,
        stepsMax: 20,
        cfgMin: 8,
        cfgMax: 6,
        variantCount: 4,
      }),
    ).toEqual(
      expect.objectContaining({
        stepsMin: 30,
        stepsMax: 30,
        cfgMin: 8,
        cfgMax: 8,
        variantCount: 4,
      }),
    );
    expect(normalizeSamplerVariation({})).toEqual({
      stepsMin: 24,
      stepsMax: 24,
      cfgMin: 7,
      cfgMax: 7,
      cfgStep: 0.1,
      randomizeSeed: false,
      variantCount: 1,
    });
  });

  it("maps batch_runs only at the durable compatibility boundary", () => {
    const adapter = new SamplerStateAdapter();

    expect(adapter.restore({ batch_runs: 3 })).toEqual({
      batch_runs: 3,
      variant_count: 3,
    });
    expect(adapter.restore({ batch_runs: 3, variant_count: 4 })).toEqual({
      batch_runs: 3,
      variant_count: 4,
    });
    expect(adapter.persist({ variant_count: 4, seed: 9 })).toEqual({
      batch_runs: 4,
      seed: 9,
    });
    expect(adapter.persist({ seed: 9 })).toEqual({
      batch_runs: 1,
      seed: 9,
    });
  });
});
