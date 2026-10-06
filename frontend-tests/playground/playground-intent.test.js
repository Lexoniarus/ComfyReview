import { describe, expect, it, vi } from "vitest";

import {
  PlaygroundIntentNavigator,
  PlaygroundIntentUrlCleaner,
  PlaygroundIntentStore,
  intentFromAnalyticsAction,
  playgroundIntentUrl,
  readPlaygroundIntent,
} from "../../static/js/playground/playground-intent.js";

describe("Playground intent codec", () => {
  it("round-trips canonical identities and render settings", () => {
    const intent = {
      promptImageUid: "image-prompt",
      renderImageUid: "image-render",
      promptCompositionUid: "prompt-composition-a",
      promptScope: {
        kind: "scene",
        component_uid: "scene-a",
        revision_uid: "scene-revision-old",
      },
      promptCombination: [
        { kind: "character", component_uid: "character-a", revision_uid: null },
        { kind: "scene", component_uid: "scene-a" },
      ],
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
    const legacy = readPlaygroundIntent(
      "?component=character-a&revision=revision-a&composition=composition-a&image=image-a",
    );
    expect(legacy).not.toHaveProperty("componentUids");
    expect(legacy).not.toHaveProperty("revisionUids");
    expect(legacy).not.toHaveProperty("compositionUid");
    expect(legacy).not.toHaveProperty("imageUid");
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
    expect(action("scope", { componentUid: "character-a" })).toEqual({});
    expect(
      action("scope", { componentUids: '["character-a","scene-a"]' }),
    ).toEqual({});
    expect(action("composition", { compositionUid: "composition-a" })).toEqual({
      promptCompositionUid: "composition-a",
    });
    expect(action("image", { imageUid: "image-a" })).toEqual({});
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
    expect(action("parameter", { parameter: "unknown", value: "1" })).toEqual(
      {},
    );
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

  it("navigates typed analytics actions through the encoded URL", () => {
    const locationRef = { assign: vi.fn() };
    const element = document.createElement("button");
    element.dataset.playgroundIntent = "scope";
    element.dataset.promptKind = "scene";
    element.dataset.componentUid = "scene-a";

    new PlaygroundIntentNavigator(locationRef).open(element);

    const navigated = readPlaygroundIntent(
      locationRef.assign.mock.calls[0][0].split("?")[1],
    );
    expect(navigated.promptScope).toEqual({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: null,
    });
  });

  it("stages only typed combination selections and encodes them in navigation", () => {
    const locationRef = { assign: vi.fn() };
    const store = new PlaygroundIntentStore(new MemoryStorage());
    store.stageRenderSetup("render-image");
    const intent = {
      promptCombination: [
        { kind: "scene", component_uid: "scene-a", revision_uid: null },
        { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
      ],
    };

    new PlaygroundIntentNavigator(locationRef, store).openIntent(intent);

    const stagedUrl = locationRef.assign.mock.calls[0][0];
    const stagedIntent = readPlaygroundIntent(stagedUrl.split("?")[1]);
    expect(stagedIntent.promptCombination).toEqual(intent.promptCombination);
    expect(stagedIntent.renderImageUid).toBe("render-image");
    expect(store.read()).toEqual({
      promptCombination: stagedIntent.promptCombination,
      renderImageUid: "render-image",
    });
  });

  it("removes only the consumed combination URL source", () => {
    const selections = [
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
      { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
    ];
    const locationRef = {
      href: `https://example.test/playground/generator?prompt_combination=${encodeURIComponent(
        JSON.stringify(selections),
      )}&render_image=render-image&view=cards#generator`,
    };
    const historyRef = {
      state: { navigation: 1 },
      replaceState: vi.fn((_state, _title, path) => {
        locationRef.href = new URL(path, locationRef.href).href;
      }),
    };
    const cleaner = new PlaygroundIntentUrlCleaner(locationRef, historyRef);

    expect(
      cleaner.removeTypedPromptSource({ type: "combination", selections }),
    ).toBe(true);
    const currentUrl = new URL(locationRef.href);
    expect(currentUrl.searchParams.has("prompt_combination")).toBe(false);
    expect(currentUrl.searchParams.get("render_image")).toBe("render-image");
    expect(currentUrl.searchParams.get("view")).toBe("cards");
    expect(currentUrl.hash).toBe("#generator");
    expect(
      readPlaygroundIntent(currentUrl.search).promptCombination,
    ).toBeUndefined();
    expect(historyRef.replaceState).toHaveBeenCalledOnce();

    expect(
      cleaner.removeTypedPromptSource({ type: "combination", selections }),
    ).toBe(false);
    expect(historyRef.replaceState).toHaveBeenCalledOnce();
  });

  it("removes matching image, composition, and scope URL sources only", () => {
    const sources = [
      {
        key: "prompt_image",
        value: "image-a",
        source: { type: "image", imageUid: "image-a" },
        mismatch: { type: "image", imageUid: "image-b" },
      },
      {
        key: "prompt_composition",
        value: "composition-a",
        source: { type: "composition", compositionUid: "composition-a" },
        mismatch: { type: "composition", compositionUid: "composition-b" },
      },
      {
        key: "prompt_scope",
        value: JSON.stringify({
          kind: "scene",
          component_uid: "scene-a",
          revision_uid: "scene-revision-a",
        }),
        source: {
          type: "scope",
          scope: {
            kind: "scene",
            component_uid: "scene-a",
            revision_uid: "scene-revision-a",
          },
        },
        mismatch: {
          type: "scope",
          scope: {
            kind: "scene",
            component_uid: "scene-b",
            revision_uid: "scene-revision-a",
          },
        },
      },
    ];

    for (const { key, value, source, mismatch } of sources) {
      const query = new URLSearchParams({
        [key]: value,
        render_image: "render-image",
      });
      const locationRef = {
        href: `https://example.test/playground/generator?${query}`,
      };
      const historyRef = {
        state: null,
        replaceState: vi.fn((_state, _title, path) => {
          locationRef.href = new URL(path, locationRef.href).href;
        }),
      };
      const cleaner = new PlaygroundIntentUrlCleaner(locationRef, historyRef);

      expect(cleaner.removeTypedPromptSource(mismatch)).toBe(false);
      expect(historyRef.replaceState).not.toHaveBeenCalled();
      expect(cleaner.removeTypedPromptSource(source)).toBe(true);
      const currentUrl = new URL(locationRef.href);
      expect(currentUrl.searchParams.has(key)).toBe(false);
      expect(currentUrl.searchParams.get("render_image")).toBe("render-image");
      expect(historyRef.replaceState).toHaveBeenCalledOnce();
      expect(cleaner.removeTypedPromptSource({ type: "unknown" })).toBe(false);
      expect(historyRef.replaceState).toHaveBeenCalledOnce();
    }
  });

  it("merges render intents without replacing a typed prompt source", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    store.stagePromptScope({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: null,
    });
    store.merge({ sampler: "euler", steps_min: 24, steps_max: 24 });
    store.merge({ sampler: "dpmpp_2m", cfg_min: 6.5, cfg_max: 6.5 });

    expect(store.read()).toEqual(
      expect.objectContaining({
        promptScope: {
          kind: "scene",
          component_uid: "scene-a",
          revision_uid: null,
        },
        sampler: "dpmpp_2m",
        steps_min: 24,
        cfg_min: 6.5,
      }),
    );
    expect(store.consumeUrl()).toContain("sampler=dpmpp_2m");
    store.clear();
    expect(store.read()).toEqual({});
  });

  it("ignores obsolete version 1 staged intents", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);

    storage.setItem(
      "comfyreview.playground-intent.v2",
      JSON.stringify({ version: 1, intent: { imageUid: "legacy" } }),
    );
    expect(store.read()).toEqual({});
    store.merge({ sampler: "euler" });
    expect(store.read()).toEqual({ sampler: "euler" });
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

  it("replaces only the typed prompt source while preserving render data", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    store.stageRenderSetup("image-render");
    store.stagePromptScope({
      kind: "scene",
      component_uid: "scene-a",
    });
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

    expect(store.read()).toEqual({
      promptCompositionUid: "composition-a",
      renderImageUid: "image-render",
    });

    store.clearPromptComposition("composition-a");
    expect(store.read()).toEqual({ renderImageUid: "image-render" });
  });

  it("clears only a matching staged combination and preserves independent sources", () => {
    const store = new PlaygroundIntentStore(new MemoryStorage());
    const selections = [
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
      { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
    ];
    store.stageRenderSetup("render-image");
    store.stagePromptCombination(selections);

    store.clearPromptCombination([
      { kind: "scene", component_uid: "scene-a", revision_uid: null },
    ]);
    expect(store.read().promptCombination).toEqual(selections);

    store.clearPromptCombination([
      { kind: "scene", component_uid: "other-scene", revision_uid: null },
      { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
    ]);
    expect(store.read().promptCombination).toEqual(selections);

    store.clearPromptCombination(selections);
    expect(store.read()).toEqual({ renderImageUid: "render-image" });
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
