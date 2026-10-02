import { describe, expect, it, vi } from "vitest";

import {
  PlaygroundIntentNavigator,
  intentFromAnalyticsAction,
  playgroundIntentUrl,
  readPlaygroundIntent,
} from "../../static/js/playground/playground-intent.js";

describe("Playground intent codec", () => {
  it("round-trips canonical identities and render settings", () => {
    const intent = {
      componentUids: ["character-a", "scene-a"],
      revisionUids: ["revision-a"],
      compositionUid: "composition-a",
      imageUid: "image-a",
      checkpoint: "model.safetensors",
      sampler: "euler",
      scheduler: "normal",
      seedMode: "fixed",
      seed: 42,
      steps_min: 20,
      steps_max: 30,
      cfg_min: 5.5,
      cfg_max: 7,
      denoise: 0.8,
    };

    const url = playgroundIntentUrl(intent);
    expect(readPlaygroundIntent(url.split("?")[1])).toEqual(intent);
    expect(
      readPlaygroundIntent("?steps_min=invalid").steps_min,
    ).toBeUndefined();
    expect(readPlaygroundIntent("").componentUids).toEqual([]);
    expect(playgroundIntentUrl({})).toBe("/playground/generator");
  });

  it("maps every analytics action without accepting prompt strings", () => {
    expect(action("scope", { componentUid: "character-a" })).toEqual({
      componentUids: ["character-a"],
    });
    expect(
      action("scope", { componentUids: '["character-a","scene-a"]' }),
    ).toEqual({ componentUids: ["character-a", "scene-a"] });
    expect(action("composition", { compositionUid: "composition-a" })).toEqual({
      compositionUid: "composition-a",
      componentUids: [],
    });
    expect(action("image", { imageUid: "image-a" })).toEqual({
      imageUid: "image-a",
    });
    expect(action("parameter", { parameter: "steps", value: "24" })).toEqual({
      steps_min: 24,
      steps_max: 24,
    });
    expect(action("parameter", { parameter: "cfg", value: "bad" })).toEqual({});
    expect(action("parameter", { parameter: "cfg", value: "6.5" })).toEqual({
      cfg_min: 6.5,
      cfg_max: 6.5,
    });
    expect(action("parameter", { parameter: "denoise", value: "1" })).toEqual(
      {},
    );
    expect(
      action("parameter", { parameter: "checkpoint", value: "model" }),
    ).toEqual({ checkpoint: "model" });
    expect(
      action("recommendation", {
        recommendation: '{"sampler":"euler","steps":30,"cfg":6}',
      }),
    ).toEqual(
      expect.objectContaining({ sampler: "euler", steps_min: 30, cfg_max: 6 }),
    );
    expect(
      action("render_setup", {
        renderSetup:
          '{"checkpoint":"model","stages":[{"sampler":"euler","steps":20}]}',
      }),
    ).toEqual(
      expect.objectContaining({ checkpoint: "model", sampler: "euler" }),
    );
    expect(action("unknown", {})).toEqual({});
  });

  it("navigates through the encoded URL", () => {
    const locationRef = { assign: vi.fn() };
    const element = document.createElement("button");
    element.dataset.playgroundIntent = "image";
    element.dataset.imageUid = "image-a";

    new PlaygroundIntentNavigator(locationRef).open(element);

    expect(locationRef.assign).toHaveBeenCalledWith(
      "/playground/generator?image=image-a",
    );
  });
});

function action(kind, values) {
  const element = document.createElement("button");
  element.dataset.playgroundIntent = kind;
  Object.assign(element.dataset, values);
  return intentFromAnalyticsAction(element);
}
