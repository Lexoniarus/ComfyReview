/** Own image-to-generator action menus, validation requests and staging. */
export class ImageGeneratorActions {
  /** @param {{api: {get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>}, store: {stagePromptSetup: (uid: string) => any, stageRenderSetup: (uid: string) => any}, eventTarget?: EventTarget}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.store = dependencies.store;
    this.eventTarget = dependencies.eventTarget || window;
    this.abortController = new AbortController();
    this.request = null;
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
        this.#button(imageUid, "prompt", "Prompt-Setup vormerken"),
        this.#button(imageUid, "render", "Generierungseinstellungen vormerken"),
      );
      root.append(toggle, menu);
      return root;
    }
    root.append(
      this.#button(imageUid, "prompt", "Prompt-Setup vormerken"),
      this.#button(imageUid, "render", "Generierungseinstellungen vormerken"),
    );
    return root;
  }

  dispose() {
    this.abortController.abort();
    this.request?.abort();
  }

  /** @param {string} imageUid @param {"prompt" | "render"} kind @param {string} label */
  #button(imageUid, kind, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = kind === "prompt" ? "secondary-button" : "ghost-button";
    button.textContent = label;
    button.addEventListener(
      "click",
      (event) => {
        event.preventDefault();
        event.stopPropagation();
        void this.#stage(button, imageUid, kind);
      },
      { signal: this.abortController.signal },
    );
    return button;
  }

  /** @param {HTMLButtonElement} button @param {string} imageUid @param {"prompt" | "render"} kind */
  async #stage(button, imageUid, kind) {
    this.request?.abort();
    this.request = new AbortController();
    button.disabled = true;
    try {
      const handoff = await this.api.get(
        `images/${encodeURIComponent(imageUid)}/generator-handoff`,
        { signal: this.request.signal },
      );
      if (kind === "render" && !handoff.render_setup?.applicable) {
        const issues = Array.isArray(handoff.render_setup?.issues)
          ? handoff.render_setup.issues.join(", ")
          : "nicht anwendbar";
        throw new Error(`Render-Setup kann nicht übernommen werden: ${issues}`);
      }
      if (kind === "prompt") this.store.stagePromptSetup(imageUid);
      else this.store.stageRenderSetup(imageUid);
      this.#notify(
        kind === "prompt"
          ? "Prompt-Setup für den Generator vorgemerkt"
          : "Generierungseinstellungen für den Generator vorgemerkt",
      );
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.#notify(
          error && typeof error === "object" && "message" in error
            ? String(error.message)
            : "Übernahme konnte nicht vorbereitet werden",
        );
      }
    } finally {
      button.disabled = false;
    }
  }

  /** @param {string} message */
  #notify(message) {
    this.eventTarget.dispatchEvent(
      new CustomEvent("comfyreview:intent-staged", { detail: { message } }),
    );
  }
}
