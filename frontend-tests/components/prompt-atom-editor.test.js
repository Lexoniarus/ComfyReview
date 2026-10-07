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
    button(rows[1], "−0,01").click();
    expect(editor.value()[1].weight).toBe(1.19);
    button(rows[1], "+0,01").click();
    expect(editor.value()[1].weight).toBe(1.2);
    button(rows[1], "Nach oben").click();
    expect(editor.value()[0].text).toBe("cyan eyes");
    button(rows[1], "Nach unten").click();
    expect(editor.value()[1].text).toBe("cyan eyes");
    button(rows[1], "Entfernen").click();
    expect(editor.value()).toEqual([{ text: "silver hair", weight: 1 }]);

    button(editor.element, "Atom hinzufügen").click();
    const added = editor.element.querySelectorAll(".prompt-atom-row")[1];
    const addedText = added.querySelector("[data-atom-text]");
    const addedWeight = added.querySelector("[data-atom-weight]");
    addedText.value = " soft smile ";
    addedText.dispatchEvent(new Event("input"));
    addedWeight.value = "1.15";
    addedWeight.dispatchEvent(new Event("input"));
    expect(editor.value()[1]).toEqual({ text: "soft smile", weight: 1.15 });

    button(editor.element, "Revision zurücksetzen").click();
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

  it("reorders with native drag and pointer drag without leaving its group", () => {
    const onChange = vi.fn();
    const editor = new PromptAtomEditor(
      "Positive Atome",
      [
        { text: "one", weight: 1 },
        { text: "two", weight: 1 },
        { text: "three", weight: 1 },
      ],
      onChange,
    );
    document.body.append(editor.element);
    const rows = editor.element.querySelectorAll(".prompt-atom-row");
    Object.defineProperty(rows[0], "getBoundingClientRect", {
      value: () => ({ top: 0, height: 20 }),
    });
    Object.defineProperty(rows[1], "getBoundingClientRect", {
      value: () => ({ top: 20, height: 20 }),
    });

    editor.list.dispatchEvent(
      new MouseEvent("dragover", { bubbles: true, clientY: 5 }),
    );
    const textTarget = document.createTextNode("pointer target");
    editor.list.append(textTarget);
    textTarget.dispatchEvent(pointerEvent("pointerdown", 90, 0));
    rows[2].dispatchEvent(new Event("dragstart"));
    editor.list.dispatchEvent(
      new MouseEvent("dragover", { bubbles: true, clientY: 5 }),
    );
    rows[2].dispatchEvent(new Event("dragend"));
    expect(editor.value().map((item) => item.text)).toEqual([
      "three",
      "one",
      "two",
    ]);

    const handle = rows[1].querySelector("[data-drag-handle]");
    handle.setPointerCapture = vi.fn();
    editor.list.dispatchEvent(pointerEvent("pointerdown", 99, 0));
    editor.list.dispatchEvent(pointerEvent("pointermove", 99, 0));
    editor.list.dispatchEvent(pointerEvent("pointerup", 99, 0));
    handle.dispatchEvent(pointerEvent("pointerdown", 7, 0));
    handle.dispatchEvent(pointerEvent("pointermove", 8, 0));
    handle.dispatchEvent(pointerEvent("pointerup", 8, 0));
    handle.dispatchEvent(pointerEvent("pointermove", 7, 100));
    handle.dispatchEvent(pointerEvent("pointercancel", 7, 100));
    expect(editor.value().at(-1).text).toBe("two");
    expect(onChange).toHaveBeenCalled();
    editor.dispose();
  });
});

function button(row, label) {
  return [...row.querySelectorAll("button")].find(
    (candidate) => candidate.textContent === label,
  );
}

function pointerEvent(type, pointerId, clientY) {
  const event = new MouseEvent(type, { bubbles: true, clientY });
  Object.defineProperty(event, "pointerId", { value: pointerId });
  return event;
}
