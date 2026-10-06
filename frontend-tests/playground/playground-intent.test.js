import { describe, expect, it, vi } from "vitest";

import {
  PlaygroundIntentNavigator,
  PlaygroundIntentStore,
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
      promptImageUid: "image-prompt",
      renderImageUid: "image-render",
      promptCompositionUid: "prompt-composition-a",
      promptScope: {
        kind: "scene",
        component_uid: "scene-a",
        revision_uid: "scene-revision-old",
      },
      checkpoint: "model.safetensors",
      sampler: "euler",
      scheduler: "normal",
      aspectFormat: "2:3",
      resolutionClass: "2160",
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
    expect(readPlaygroundIntent("?prompt_scope=invalid").promptScope).toEqual({
      kind: "",
      component_uid: "",
      revision_uid: null,
    });
    expect(readPlaygroundIntent("").componentUids).toEqual([]);
    expect(playgroundIntentUrl({})).toBe("/playground/generator");
  });

  it("maps every analytics action without accepting prompt strings", () => {
    expect(
      action("scope", {
        componentUid: "scene-a",
        promptKind: "scene",
        revisionUid: "scene-revision-old",
      }),
    ).toEqual({
      promptScope: {
        kind: "scene",
        component_uid: "scene-a",
        revision_uid: "scene-revision-old",
      },
    });
    expect(action("scope", { componentUid: "character-a" })).toEqual({
      componentUids: ["character-a"],
    });
    expect(
      action("scope", { componentUids: '["character-a","scene-a"]' }),
    ).toEqual({ componentUids: ["character-a", "scene-a"] });
    expect(action("composition", { compositionUid: "composition-a" })).toEqual({
      promptCompositionUid: "composition-a",
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
    expect(action("parameter", { parameter: "denoise", value: "1" })).toEqual({
      denoise: 1,
    });
    expect(
      action("parameter", { parameter: "aspect_format", value: "9:16" }),
    ).toEqual({ aspectFormat: "9:16" });
    expect(
      action("parameter", { parameter: "resolution_class", value: "720" }),
    ).toEqual({ resolutionClass: "720" });
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

  it("stages prompt and render intents per tab with deterministic merging", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    store.merge({ componentUids: ["character-a"] });
    store.merge({ componentUids: ["character-b"] });
    store.merge({ componentUids: ["scene-a"] });
    store.merge({ sampler: "euler", steps_min: 24, steps_max: 24 });
    store.merge({ sampler: "dpmpp_2m", cfg_min: 6.5, cfg_max: 6.5 });
    const previousState = JSON.parse(
      storage.getItem("comfyreview.playground-intent.v2"),
    );
    previousState.prompt_kinds.character = "character-b";
    storage.setItem(
      "comfyreview.playground-intent.v2",
      JSON.stringify(previousState),
    );
    store.merge({
      compositionUid: "composition-a",
      componentUids: ["character-c"],
      revisionUids: ["revision-old"],
    });
    store.merge({
      componentUids: ["scene-b"],
      revisionUids: ["revision-new"],
    });

    expect(store.read()).toEqual(
      expect.objectContaining({
        componentUids: ["character-c", "scene-b"],
        sampler: "dpmpp_2m",
        steps_min: 24,
        cfg_min: 6.5,
        revisionUids: ["revision-new"],
      }),
    );
    expect(store.consumeUrl()).toContain("sampler=dpmpp_2m");
    expect(store.read()).toEqual(
      expect.objectContaining({ sampler: "dpmpp_2m" }),
    );
    store.clear();
    expect(store.read()).toEqual({});
    expect(action("parameter", { parameter: "unknown", value: "1" })).toEqual(
      {},
    );
  });

  it("keeps image prompt and render packages independent until applied", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);

    store.stagePromptSetup({
      component_uids: ["character-a", "scene-a"],
      loras: [{ lora_uid: "lora-style", revision_uid: "revision-1" }],
    });
    store.stageRenderSetup("image-render");
    expect(store.read()).toEqual({
      componentUids: ["character-a", "scene-a"],
      loras: [{ lora_uid: "lora-style", revision_uid: "revision-1" }],
      renderImageUid: "image-render",
    });
    store.clearPrompt();
    expect(store.read()).toEqual({ renderImageUid: "image-render" });
    store.stagePromptSetup({ component_uids: ["character-new"] });
    store.clearRender();
    expect(store.read()).toEqual({
      componentUids: ["character-new"],
      loras: [],
    });

    storage.setItem(
      "comfyreview.playground-intent.v2",
      JSON.stringify({ version: 1, intent: { imageUid: "legacy" } }),
    );
    expect(store.read()).toEqual({ imageUid: "legacy" });
    store.merge({ sampler: "euler" });
    expect(store.read()).toEqual(
      expect.objectContaining({ imageUid: "legacy", sampler: "euler" }),
    );
  });

  it("stages only the prompt image identity and clears only that source", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    store.stageRenderSetup("image-render");
    store.stagePromptImage("image-prompt");

    expect(store.read()).toEqual({
      promptImageUid: "image-prompt",
      renderImageUid: "image-render",
    });

    store.clearPromptImage("another-image");
    expect(store.read()).toEqual({
      promptImageUid: "image-prompt",
      renderImageUid: "image-render",
    });

    store.clearPromptImage("image-prompt");
    expect(store.read()).toEqual({ renderImageUid: "image-render" });
  });

  it("stages one typed prompt source without modifying legacy prompt or render data", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    store.merge({
      componentUids: ["legacy-character"],
      revisionUids: ["legacy-revision"],
      compositionUid: "legacy-composition",
    });
    store.stageRenderSetup("image-render");
    store.mergePromptComponent("scene-a", "scene");
    store.clearPromptScope({
      kind: "scene",
      component_uid: "other-scene",
    });
    expect(store.read()).toHaveProperty("promptScope");
    store.clearPromptScope({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: null,
    });
    store.stagePromptScope({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: "scene-revision-1",
    });
    store.stagePromptComposition("composition-a");
    store.clearPromptComposition("another-composition");
    store.clearPromptScope({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: "scene-revision-1",
    });

    expect(store.read()).toEqual({
      componentUids: ["legacy-character"],
      revisionUids: ["legacy-revision"],
      compositionUid: "legacy-composition",
      promptCompositionUid: "composition-a",
      renderImageUid: "image-render",
    });

    store.clearPromptComposition("composition-a");
    expect(store.read()).toEqual({
      componentUids: ["legacy-character"],
      revisionUids: ["legacy-revision"],
      compositionUid: "legacy-composition",
      renderImageUid: "image-render",
    });
  });

  it("keeps the legacy source-identity merge contract", () => {
    const store = new PlaygroundIntentStore(new MemoryStorage());
    store.merge({
      componentUids: ["character-a"],
      promptImageUid: "image-prompt",
      loras: [],
    });

    expect(store.read()).toEqual({
      promptImageUid: "image-prompt",
      loras: [],
    });
  });
});

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }
  getItem(key) {
    return this.values.get(key) ?? null;
  }
  setItem(key, value) {
    this.values.set(key, String(value));
  }
  removeItem(key) {
    this.values.delete(key);
  }
}

function action(kind, values) {
  const element = document.createElement("button");
  element.dataset.playgroundIntent = kind;
  Object.assign(element.dataset, values);
  return intentFromAnalyticsAction(element);
}
