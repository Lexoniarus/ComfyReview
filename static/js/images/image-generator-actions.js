/** Own the shared image-to-generator action presentation. */
export class ImageGeneratorActions {
  /** @param {import("../playground/playground-intent.js").GeneratorHandoffNavigator} navigator */
  constructor(navigator) {
    this.navigator = navigator;
    this.abortController = new AbortController();
  }

  /** @param {string} imageUid @param {"compact" | "prominent"} [variant] */
  create(imageUid, variant = "compact") {
    const root = document.createElement("div");
    root.className = `image-generator-actions image-generator-actions-${variant}`;
    if (variant === "compact") {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "icon-button image-generator-actions-toggle";
      toggle.setAttribute("aria-label", "Im Generator verwenden");
      toggle.setAttribute("aria-expanded", "false");
      toggle.textContent = "⋯";
      const menu = document.createElement("div");
      menu.className = "image-generator-actions-menu";
      menu.hidden = true;
      toggle.addEventListener(
        "click",
        (event) => {
          event.preventDefault();
          event.stopPropagation();
          menu.hidden = !menu.hidden;
          toggle.setAttribute("aria-expanded", String(!menu.hidden));
        },
        { signal: this.abortController.signal },
      );
      menu.append(
        this.#button(imageUid, "prompt", "compact"),
        this.#button(imageUid, "render", "compact"),
      );
      root.append(toggle, menu);
      return root;
    }
    root.append(
      this.#button(imageUid, "prompt", "prominent"),
      this.#button(imageUid, "render", "prominent"),
    );
    return root;
  }

  dispose() {
    this.abortController.abort();
  }

  /** @param {string} imageUid @param {"prompt" | "render"} kind @param {"compact" | "prominent"} variant */
  #button(imageUid, kind, variant) {
    const button = createGeneratorHandoffAction(kind, { variant });
    button.addEventListener(
      "click",
      (event) => {
        event.preventDefault();
        event.stopPropagation();
        this.navigator.openIntent(
          kind === "prompt"
            ? { kind: "image-prompt", imageUid }
            : { kind: "image-render", imageUid },
        );
      },
      { signal: this.abortController.signal },
    );
    return button;
  }
}
import { createGeneratorHandoffAction } from "../playground/generator-handoff-action.js";
