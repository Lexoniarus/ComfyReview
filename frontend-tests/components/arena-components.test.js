import { beforeEach, describe, expect, it, vi } from "vitest";

import { ArenaBoard } from "../../static/js/arena/arena-board.js";
import { ArenaKeyboard } from "../../static/js/arena/arena-keyboard.js";

describe("arena components", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders pair controls and owns their actions", () => {
    const root = document.createElement("div");
    const onDecision = vi.fn();
    const onInspect = vi.fn();
    const onExpand = vi.fn();
    const createGeneratorActions = vi.fn(() => document.createElement("menu"));
    const board = new ArenaBoard(root, {
      onDecision,
      onInspect,
      onExpand,
      createGeneratorActions,
    });
    const pair = {
      left: { image_uid: "left", image_url: "/left.png" },
      right: { image_uid: "right", image_url: "/right.png" },
    };

    board.loading();
    expect(root.textContent).toContain("geladen");
    board.empty();
    expect(root.textContent).toContain("abgeschlossen");
    board.error("");
    expect(root.textContent).toContain("konnte nicht");
    board.render(pair);
    expect(createGeneratorActions).toHaveBeenCalledTimes(2);
    root
      .querySelector("[data-arena-action='decide'][data-side='left']")
      ?.click();
    root
      .querySelector("[data-arena-action='inspect'][data-side='right']")
      ?.click();
    root
      .querySelector("[data-arena-action='expand'][data-side='right']")
      ?.click();
    expect(onDecision).toHaveBeenCalledWith("left");
    expect(onInspect).toHaveBeenCalledWith(pair.right);
    expect(onExpand).toHaveBeenCalledWith("/right.png");
    board.setBusy(true);
    expect(root.querySelector("button")?.disabled).toBe(true);
    board.setBusy(false);
    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    board.dispose();
  });

  it("routes arrow shortcuts outside editing and modified states", () => {
    const onDecision = vi.fn();
    const keyboard = new ArenaKeyboard(document, { onDecision });

    document.dispatchEvent(key("ArrowLeft"));
    document.dispatchEvent(key("ArrowRight"));
    document.dispatchEvent(key("x"));
    expect(onDecision.mock.calls).toEqual([["left"], ["right"]]);

    const input = document.createElement("input");
    document.body.append(input);
    input.dispatchEvent(key("ArrowLeft"));
    document.dispatchEvent(key("ArrowLeft", { ctrlKey: true }));
    document.dispatchEvent(key("ArrowLeft", { metaKey: true }));
    document.dispatchEvent(key("ArrowLeft", { altKey: true }));
    const prevented = key("ArrowLeft");
    prevented.preventDefault();
    document.dispatchEvent(prevented);
    expect(onDecision).toHaveBeenCalledTimes(2);
    keyboard.dispose();
  });
});

function key(value, options = {}) {
  return new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key: value,
    ...options,
  });
}
