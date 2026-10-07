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
    this.currentStep = "setup";
    this.hasVariants = false;
    for (const button of this.buttons) {
      button.addEventListener(
        "click",
        () => this.show(String(button.dataset.workspaceStep || "setup")),
        { signal: this.abortController.signal },
      );
    }
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
    if (notify) this.onStepChange();
    return true;
  }

  dispose() {
    this.abortController.abort();
  }
}
