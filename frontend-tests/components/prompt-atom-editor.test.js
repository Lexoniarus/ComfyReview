import { beforeEach, describe, expect, it, vi } from "vitest";

import { PromptAtomEditor } from "../../static/js/prompts/prompt-atom-editor.js";

describe("Prompt atom editor", () => {
  beforeEach(() => document.body.replaceChildren());

  it("owns ordered atom editing, movement, removal and reset", () => {
    const onChange = vi.fn();
    const editor = new PromptAtomEditor(
      "Positive Atome",
      [
        { text: "silver hair", weight: 1 },
        { text: "cyan eyes", weight: 1.2 },
      ],
      onChange,
    );
    document.body.append(editor.element);

    expect(editor.value()).toEqual([
      { text: "silver hair", weight: 1 },
      { text: "cyan eyes", weight: 1.2 },
    ]);
    const rows = editor.element.querySelectorAll(".prompt-atom-row");
    rows[1].querySelectorAll("button")[0].click();
    expect(editor.value()[0].text).toBe("cyan eyes");
    rows[1].querySelectorAll("button")[1].click();
    expect(editor.value()[1].text).toBe("cyan eyes");
    rows[1].querySelectorAll("button")[2].click();
    expect(editor.value()).toEqual([{ text: "silver hair", weight: 1 }]);

    editor.element.querySelectorAll(":scope > button")[0].click();
    const added = editor.element.querySelectorAll(".prompt-atom-row")[1];
    const addedText = added.querySelector("[data-atom-text]");
    const addedWeight = added.querySelector("[data-atom-weight]");
    addedText.value = " soft smile ";
    addedText.dispatchEvent(new Event("input"));
    addedWeight.value = "1.15";
    addedWeight.dispatchEvent(new Event("input"));
    expect(editor.value()[1]).toEqual({ text: "soft smile", weight: 1.15 });

    editor.element.querySelectorAll(":scope > button")[1].click();
    expect(editor.value()).toHaveLength(2);
    expect(onChange).toHaveBeenCalled();
    editor.dispose();
  });

  it("normalizes missing input and ignores blank rows", () => {
    const editor = new PromptAtomEditor("Negative Atome", null);
    const incomplete = document.createElement("div");
    incomplete.className = "prompt-atom-row";
    editor.list.append(incomplete);

    expect(editor.value()).toEqual([]);
    editor.dispose();
  });
});
