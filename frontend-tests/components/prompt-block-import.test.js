import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  parsePromptBlock,
  PromptAtomEditor,
} from "../../static/js/prompts/prompt-atom-editor.js";

describe("Prompt block import", () => {
  beforeEach(() => document.body.replaceChildren());

  it("parses weighted, unweighted and multiline ComfyUI prompt atoms", () => {
    expect(
      parsePromptBlock(`
        (masterpiece:1.3), (best quality:1.3), solo,
        (hair with red, gold tips:1.25)
        (friendly expression:1.2)
      `),
    ).toEqual([
      { text: "masterpiece", weight: 1.3 },
      { text: "best quality", weight: 1.3 },
      { text: "solo", weight: 1 },
      { text: "hair with red, gold tips", weight: 1.25 },
      { text: "friendly expression", weight: 1.2 },
    ]);
    expect(parsePromptBlock("(), (:1.2)")).toEqual([]);
  });

  it("normalizes incomplete initial usages to safe defaults", () => {
    const editor = new PromptAtomEditor("Positive Atome", [{}]);
    document.body.append(editor.element);

    expect(editor.value()).toEqual([]);
    const row = editor.element.querySelector(".prompt-atom-row");
    expect(row.querySelector("[data-atom-text]").value).toBe("");
    expect(row.querySelector("[data-atom-weight]").value).toBe("1");
    editor.dispose();
  });

  it("replaces or appends atoms from one pasted prompt block", () => {
    const onChange = vi.fn();
    const editor = new PromptAtomEditor(
      "Positive Atome",
      [{ text: "old atom", weight: 1 }],
      onChange,
    );
    document.body.append(editor.element);

    button(editor.element, "Prompt-Block einfügen").click();
    const input = editor.element.querySelector("[data-prompt-block-input]");
    expect(input).toBeInstanceOf(HTMLTextAreaElement);
    input.value = "(masterpiece:1.3), (best quality:1.3), solo";
    button(editor.element, "Ersetzen").click();

    expect(editor.value()).toEqual([
      { text: "masterpiece", weight: 1.3 },
      { text: "best quality", weight: 1.3 },
      { text: "solo", weight: 1 },
    ]);

    button(editor.element, "Prompt-Block einfügen").click();
    input.value = "(cyan eyes:1.45), (soft blush:1.1)";
    button(editor.element, "Anhängen").click();

    expect(editor.value()).toEqual([
      { text: "masterpiece", weight: 1.3 },
      { text: "best quality", weight: 1.3 },
      { text: "solo", weight: 1 },
      { text: "cyan eyes", weight: 1.45 },
      { text: "soft blush", weight: 1.1 },
    ]);
    expect(onChange).toHaveBeenCalledTimes(2);
    editor.dispose();
  });

  it("keeps the importer open and reports empty input instead of changing atoms", () => {
    const onChange = vi.fn();
    const editor = new PromptAtomEditor(
      "Negative Atome",
      [{ text: "bad anatomy", weight: 1.5 }],
      onChange,
    );
    document.body.append(editor.element);

    button(editor.element, "Prompt-Block einfügen").click();
    button(editor.element, "Ersetzen").click();

    expect(editor.value()).toEqual([{ text: "bad anatomy", weight: 1.5 }]);
    expect(
      editor.element.querySelector("[data-prompt-block-status]").textContent,
    ).toContain("Keine gültigen");
    expect(onChange).not.toHaveBeenCalled();
    editor.dispose();
  });

  it("cancels the importer without changing atoms or notifying changes", () => {
    const onChange = vi.fn();
    const editor = new PromptAtomEditor(
      "Positive Atome",
      [{ text: "keep me", weight: 1.2 }],
      onChange,
    );
    document.body.append(editor.element);

    button(editor.element, "Prompt-Block einfügen").click();
    const panel = editor.element.querySelector(".prompt-block-import");
    const status = editor.element.querySelector("[data-prompt-block-status]");
    const input = editor.element.querySelector("[data-prompt-block-input]");
    if (
      !(panel instanceof HTMLElement) ||
      !(status instanceof HTMLElement) ||
      !(input instanceof HTMLTextAreaElement)
    ) {
      throw new Error("Prompt block importer did not render");
    }

    input.value = "temporary value";
    status.textContent = "temporary status";
    button(editor.element, "Abbrechen").click();

    expect(panel.hidden).toBe(true);
    expect(status.textContent).toBe("");
    expect(editor.value()).toEqual([{ text: "keep me", weight: 1.2 }]);
    expect(onChange).not.toHaveBeenCalled();
    editor.dispose();
  });
});

function button(root, label) {
  return [...root.querySelectorAll("button")].find(
    (candidate) => candidate.textContent === label,
  );
}
