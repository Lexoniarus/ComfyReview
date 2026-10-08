import { describe, expect, it, vi } from "vitest";

import {
  GeneratorHandoffNavigator,
  GeneratorHandoffUrlCleaner,
  intentFromAnalyticsAction,
  playgroundIntentUrl,
  readPlaygroundIntent,
} from "../../static/js/playground/playground-intent.js";

describe("Playground intent codec", () => {
  it("round-trips canonical identities and render settings", () => {
    expect(
      readPlaygroundIntent(
        playgroundIntentUrl({
          kind: "image-prompt",
          imageUid: "image-a",
        }).split("?")[1],
      ).promptImageUid,
    ).toBe("image-a");
    expect(
      readPlaygroundIntent(
        playgroundIntentUrl({
          kind: "image-render",
          imageUid: "image-b",
        }).split("?")[1],
      ).renderImageUid,
    ).toBe("image-b");
    expect(
      readPlaygroundIntent(
        playgroundIntentUrl({
          kind: "render-settings",
          settings: {
            checkpoint: "model.safetensors",
            sampler: "euler",
            steps_min: 20,
            steps_max: 30,
          },
        }).split("?")[1],
      ),
    ).toEqual(
      expect.objectContaining({
        checkpoint: "model.safetensors",
        sampler: "euler",
        steps_min: 20,
        steps_max: 30,
      }),
    );
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
    expect(
      playgroundIntentUrl({
        kind: "parameter",
        parameter: "unknown",
        value: "1",
      }),
    ).toBe("/playground/generator");
    expect(
      playgroundIntentUrl({
        kind: "parameter",
        parameter: "cfg",
        value: "invalid",
      }),
    ).toBe("/playground/generator");
    expect(
      readPlaygroundIntent(
        playgroundIntentUrl({
          kind: "composition",
          compositionUid: "composition-a",
        }).split("?")[1],
      ).promptCompositionUid,
    ).toBe("composition-a");
    expect(
      readPlaygroundIntent("?prompt_composition=composition-a")
        .promptCompositionUid,
    ).toBe("composition-a");

    const variants = [
      ["checkpoint", "model", { checkpoint: "model" }],
      ["aspect_format", "9:16", { aspectFormat: "9:16" }],
      ["resolution_class", "720", { resolutionClass: "720" }],
      ["steps", "24", { steps_min: 24, steps_max: 24 }],
      ["cfg", "6.5", { cfg_min: 6.5, cfg_max: 6.5 }],
      ["denoise", "0.8", { denoise: 0.8 }],
    ];
    for (const [parameter, value, expected] of variants) {
      const encoded = playgroundIntentUrl({
        kind: "parameter",
        parameter,
        value,
      });
      expect(readPlaygroundIntent(encoded.split("?")[1])).toEqual(
        expect.objectContaining(expected),
      );
    }
    expect(
      playgroundIntentUrl(/** @type {any} */ ({ kind: "unsupported" })),
    ).toBe("/playground/generator");
  });

  it("maps every analytics action without accepting prompt strings", () => {
    expect(
      action("scope", {
        componentUid: "scene-a",
        promptKind: "scene",
        revisionUid: "scene-revision-old",
      }),
    ).toEqual({
      kind: "scope",
      scope: {
        kind: "scene",
        component_uid: "scene-a",
        revision_uid: "scene-revision-old",
      },
    });
    expect(action("scope", { componentUid: "character-a" })).toBeNull();
    expect(
      action("scope", { componentUids: '["character-a","scene-a"]' }),
    ).toBeNull();
    expect(action("composition", { compositionUid: "composition-a" })).toEqual({
      kind: "composition",
      compositionUid: "composition-a",
    });
    expect(action("best_image_prompt", { imageUid: "image-best" })).toEqual({
      kind: "image-prompt",
      imageUid: "image-best",
    });
    expect(action("best_image_prompt", { imageUid: " " })).toBeNull();
    expect(action("image", { imageUid: "image-a" })).toBeNull();
    expect(action("parameter", { parameter: "steps", value: "24" })).toEqual({
      kind: "parameter",
      parameter: "steps",
      value: "24",
    });
    expect(action("parameter", { parameter: "cfg", value: "bad" })).toEqual({
      kind: "parameter",
      parameter: "cfg",
      value: "bad",
    });
    expect(
      action("recommendation", {
        recommendation: '{"sampler":"euler","steps":30,"cfg":6}',
      }),
    ).toEqual({
      kind: "render-settings",
      settings: expect.objectContaining({
        sampler: "euler",
        steps_min: 30,
        cfg_max: 6,
      }),
    });
    expect(
      action("render_setup", {
        renderSetup:
          '{"checkpoint":"model","stages":[{"sampler":"euler","steps":20}]}',
      }),
    ).toEqual({
      kind: "render-settings",
      settings: expect.objectContaining({
        checkpoint: "model",
        sampler: "euler",
      }),
    });
    expect(action("unknown", {})).toBeNull();
  });

  it("navigates typed analytics actions through the encoded URL", () => {
    const locationRef = { assign: vi.fn() };
    const element = document.createElement("button");
    element.dataset.playgroundIntent = "scope";
    element.dataset.promptKind = "scene";
    element.dataset.componentUid = "scene-a";

    new GeneratorHandoffNavigator(locationRef).open(element);

    const navigated = readPlaygroundIntent(
      locationRef.assign.mock.calls[0][0].split("?")[1],
    );
    expect(navigated.promptScope).toEqual({
      kind: "scene",
      component_uid: "scene-a",
      revision_uid: null,
    });
  });

  it("navigates combination selections directly without hidden staging", () => {
    const locationRef = { assign: vi.fn() };
    const intent = {
      kind: "combination",
      selections: [
        { kind: "scene", component_uid: "scene-a", revision_uid: null },
        { kind: "outfit", component_uid: "outfit-a", revision_uid: null },
      ],
    };

    new GeneratorHandoffNavigator(locationRef).openIntent(intent);

    const navigatedUrl = locationRef.assign.mock.calls[0][0];
    expect(readPlaygroundIntent(navigatedUrl.split("?")[1])).toEqual(
      expect.objectContaining({ promptCombination: intent.selections }),
    );
    expect(locationRef.assign).toHaveBeenCalledOnce();
  });

  it("removes every applied handoff field and preserves unrelated URL state", () => {
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
    const cleaner = new GeneratorHandoffUrlCleaner(locationRef, historyRef);

    expect(cleaner.removeHandoff()).toBe(true);
    const currentUrl = new URL(locationRef.href);
    expect(currentUrl.searchParams.has("prompt_combination")).toBe(false);
    expect(currentUrl.searchParams.has("render_image")).toBe(false);
    expect(currentUrl.searchParams.get("view")).toBe("cards");
    expect(currentUrl.hash).toBe("#generator");
    expect(
      readPlaygroundIntent(currentUrl.search).promptCombination,
    ).toBeUndefined();
    expect(historyRef.replaceState).toHaveBeenCalledOnce();

    expect(cleaner.removeHandoff()).toBe(false);
    expect(historyRef.replaceState).toHaveBeenCalledOnce();
  });
});

function action(kind, values) {
  const element = document.createElement("button");
  element.dataset.playgroundIntent = kind;
  Object.assign(element.dataset, values);
  return intentFromAnalyticsAction(element);
}
