import { describe, expect, it } from "vitest";

import { combinationPromptPatch } from "../../static/js/playground/generator-prompt-projector.js";

describe("Combination prompt projection", () => {
  it("projects only supplied kinds as fixed selections", () => {
    expect(
      combinationPromptPatch([
        { kind: "scene", component_uid: "scene-a" },
        {
          kind: "outfit",
          component_uid: "outfit-a",
          revision_uid: "outfit-revision-3",
        },
      ]),
    ).toEqual({
      loras: [],
      selections: [
        {
          kind: "scene",
          mode: "fixed",
          component_uid: "scene-a",
          revision_uid: null,
        },
        {
          kind: "outfit",
          mode: "fixed",
          component_uid: "outfit-a",
          revision_uid: "outfit-revision-3",
        },
      ],
    });
  });

  it("rejects duplicate kinds, unknown kinds, missing UIDs, and empty input", () => {
    expect(() =>
      combinationPromptPatch([
        { kind: "scene", component_uid: "scene-a" },
        { kind: "scene", component_uid: "scene-b" },
      ]),
    ).toThrow("Prompt-Rolle mehrfach vorhanden: scene");
    expect(() =>
      combinationPromptPatch([{ kind: "unknown", component_uid: "item-a" }]),
    ).toThrow("Unbekannte Prompt-Rolle: unknown");
    expect(() =>
      combinationPromptPatch([{ kind: "outfit", component_uid: " " }]),
    ).toThrow("Prompt-Rolle unvollständig: outfit");
    expect(() => combinationPromptPatch([])).toThrow(
      "Combination enthält keine Prompt-Auswahlen.",
    );
    expect(() => combinationPromptPatch("not-selections")).toThrow(
      "Combination enthält keine Prompt-Auswahlen.",
    );
  });
});
