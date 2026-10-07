/** Own the two-step Setup and Varianten workspace navigation. */
export class PlaygroundWorkspace {
  /** @param {HTMLElement} root @param {() => void} [onStepChange] */
  constructor(root, onStepChange = () => {}) {
    this.root = root;
    this.onStepChange = onStepChange;
    this.abortController = new AbortController();
    /** @type {HTMLButtonElement[]} */
    this.buttons = [...root.querySelectorAll("[data-workspace-step]")].filter(
      (item) => item instanceof HTMLButtonElement,
    );
    /** @type {Map<string | undefined, HTMLElement>} */
    this.panels = new Map(
      [...root.querySelectorAll("[data-workspace-panel]")]
        .filter((panel) => panel instanceof HTMLElement)
        .map((panel) => [panel.dataset.workspacePanel, panel]),
    );
    /** @type {HTMLButtonElement[]} */
    this.variantViewButtons = [
      ...root.querySelectorAll("[data-variant-view]"),
    ].filter((item) => item instanceof HTMLButtonElement);
    /** @type {HTMLButtonElement[]} */
    this.inspectorCloseButtons = [
      ...root.querySelectorAll("[data-close-variant-inspector]"),
    ].filter((item) => item instanceof HTMLButtonElement);
    this.currentStep = "setup";
    this.hasVariants = false;
    for (const button of this.buttons) {
      button.addEventListener(
        "click",
        () => this.show(String(button.dataset.workspaceStep || "setup")),
        { signal: this.abortController.signal },
      );
    }
    for (const button of this.variantViewButtons) {
      button.addEventListener(
        "click",
        () => this.setVariantView(String(button.dataset.variantView)),
        { signal: this.abortController.signal },
      );
    }
    for (const button of this.inspectorCloseButtons) {
      button.addEventListener("click", () => this.closeInspector(), {
        signal: this.abortController.signal,
      });
    }
    this.setVariantView("board", false);
    this.show("setup", false);
  }

  /** @param {boolean} available */
  setVariantsAvailable(available) {
    this.hasVariants = available;
    const button = this.buttons.find(
      (item) => item.dataset.workspaceStep === "variants",
    );
    if (button instanceof HTMLButtonElement) button.disabled = !available;
    if (!available && this.currentStep === "variants") this.show("setup");
    if (!available) this.closeInspector(false);
  }

  /** @param {string} step @param {boolean} [notify] */
  show(step, notify = true) {
    const requested = step === "variants" ? "variants" : "setup";
    if (requested === "variants" && !this.hasVariants) return false;
    this.currentStep = requested;
    for (const button of this.buttons) {
      const active = button.dataset.workspaceStep === requested;
      button.setAttribute("aria-selected", String(active));
      button.dataset.active = String(active);
    }
    for (const [name, panel] of this.panels) panel.hidden = name !== requested;
    if (requested === "setup") this.closeInspector(false);
    if (notify) this.onStepChange();
    return true;
  }

  /** Show the selected tablet variant view without changing the main step. */
  /** @param {string} view @param {boolean} [focus] */
  setVariantView(view, focus = false) {
    const selected = view === "inspector" ? "inspector" : "board";
    this.root.dataset.variantView = selected;
    this.root.dataset.inspectorOpen = String(selected === "inspector");
    for (const button of this.variantViewButtons) {
      const active = button.dataset.variantView === selected;
      button.setAttribute("aria-selected", String(active));
      button.dataset.active = String(active);
      if (active && focus) button.focus();
    }
  }

  /** Reveal the inspector as a laptop drawer or tablet tab. */
  openInspector() {
    this.setVariantView("inspector");
  }

  /** Return to the variant board and close any responsive drawer. */
  /** @param {boolean} [focus] */
  closeInspector(focus = true) {
    this.setVariantView("board", focus);
  }

  dispose() {
    this.abortController.abort();
  }
}
