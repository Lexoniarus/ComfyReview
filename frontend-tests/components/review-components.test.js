import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmationDialog } from "../../static/js/components/confirmation-dialog.js";
import { ReviewKeyboard } from "../../static/js/review/review-keyboard.js";
import { ReviewStage } from "../../static/js/review/review-stage.js";

describe("review components", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders candidate controls and owns their actions", () => {
    const root = document.createElement("div");
    const onRate = vi.fn();
    const onDelete = vi.fn();
    const onExpand = vi.fn();
    const createGeneratorActions = vi.fn(() => document.createElement("menu"));
    const stage = new ReviewStage(root, {
      onRate,
      onDelete,
      onExpand,
      createGeneratorActions,
    });

    stage.loading();
    expect(root.textContent).toContain("geladen");
    stage.loading("Bitte warten");
    expect(root.textContent).toContain("Bitte warten");
    stage.empty();
    expect(root.textContent).toContain("kein Bild");
    stage.error("");
    expect(root.textContent).toContain("konnte nicht");
    stage.render({ image_uid: "image-1", image_url: "/files/image.png" });
    expect(createGeneratorActions).toHaveBeenCalledOnce();
    root.querySelector("[data-rating='7']")?.click();
    root.querySelector("[data-review-action='delete']")?.click();
    root.querySelector("[data-review-action='expand']")?.click();
    expect(onRate).toHaveBeenCalledWith(7);
    expect(onDelete).toHaveBeenCalledOnce();
    expect(onExpand).toHaveBeenCalledWith("/files/image.png");
    stage.setBusy(true);
    expect(root.querySelector("button")?.disabled).toBe(true);
    stage.setBusy(false);
    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    stage.dispose();
  });

  it("routes review shortcuts except in blocked editing states", () => {
    const onRate = vi.fn();
    const onDelete = vi.fn();
    let dialogOpen = false;
    const keyboard = new ReviewKeyboard(document, {
      onRate,
      onDelete,
      isDialogOpen: () => dialogOpen,
    });

    document.dispatchEvent(key("1"));
    document.dispatchEvent(key("0"));
    document.dispatchEvent(key("Delete"));
    document.dispatchEvent(key("x"));
    expect(onRate).toHaveBeenNthCalledWith(1, 1);
    expect(onRate).toHaveBeenNthCalledWith(2, 10);
    expect(onDelete).toHaveBeenCalledOnce();

    const input = document.createElement("input");
    document.body.append(input);
    input.dispatchEvent(key("2"));
    dialogOpen = true;
    document.dispatchEvent(key("3"));
    dialogOpen = false;
    document.dispatchEvent(key("4", { ctrlKey: true }));
    document.dispatchEvent(key("5", { metaKey: true }));
    document.dispatchEvent(key("6", { altKey: true }));
    const prevented = key("7");
    prevented.preventDefault();
    document.dispatchEvent(prevented);
    expect(onRate).toHaveBeenCalledTimes(2);
    keyboard.dispose();
  });

  it("resolves confirmation, cancellation, replacement, and disposal", async () => {
    const dialog = createDialog();
    const confirmation = new ConfirmationDialog(dialog);

    dialog.click();
    const textTarget = document.createTextNode("text");
    dialog.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));

    const accepted = confirmation.confirm("Wirklich?");
    dialog.querySelector("[data-confirm-result='confirm']")?.click();
    await expect(accepted).resolves.toBe(true);

    const cancelled = confirmation.confirm("Nochmal?");
    dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
    await expect(cancelled).resolves.toBe(false);

    const replaced = confirmation.confirm("Alt");
    const current = confirmation.confirm("Neu");
    await expect(replaced).resolves.toBe(false);
    expect(confirmation.isOpen()).toBe(true);
    confirmation.dispose();
    await expect(current).resolves.toBe(false);
  });

  it("rejects an incomplete confirmation dialog", () => {
    expect(
      () => new ConfirmationDialog(document.createElement("dialog")),
    ).toThrow("message element");
  });
});

function createDialog() {
  const dialog = document.createElement("dialog");
  dialog.innerHTML =
    "<p data-confirm-message></p>" +
    "<button data-confirm-result='confirm'></button>" +
    "<button data-confirm-result='cancel'></button>";
  dialog.showModal = vi.fn(() => dialog.setAttribute("open", ""));
  dialog.close = vi.fn(() => dialog.removeAttribute("open"));
  document.body.append(dialog);
  return dialog;
}

function key(value, options = {}) {
  return new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key: value,
    ...options,
  });
}
