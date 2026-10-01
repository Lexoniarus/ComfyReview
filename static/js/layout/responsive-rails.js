/** Own mutually exclusive scope and inspector drawer state. */
export class ResponsiveRails {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    this.events = new AbortController();
    this.root.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const button = target.closest("[data-rail-action]");
        if (!(button instanceof HTMLElement)) return;
        const rail = button.dataset.railAction;
        if (rail === "scope" || rail === "inspector") this.toggle(rail);
      },
      { signal: this.events.signal },
    );
  }

  /** @param {"scope" | "inspector"} rail */
  toggle(rail) {
    this.#setOpen(rail, !this.#isOpen(rail));
  }

  /** @param {"scope" | "inspector"} rail */
  open(rail) {
    this.#setOpen(rail, true);
  }

  /** @param {"scope" | "inspector"} rail @param {boolean} shouldOpen */
  #setOpen(rail, shouldOpen) {
    const openedClass =
      rail === "scope" ? "is-scope-open" : "is-inspector-open";
    const otherClass = rail === "scope" ? "is-inspector-open" : "is-scope-open";
    this.root.classList.toggle(openedClass, shouldOpen);
    if (shouldOpen) this.root.classList.remove(otherClass);
    this.#reflect("scope", "is-scope-open");
    this.#reflect("inspector", "is-inspector-open");
  }

  /** @param {"scope" | "inspector"} rail */
  #isOpen(rail) {
    return this.root.classList.contains(
      rail === "scope" ? "is-scope-open" : "is-inspector-open",
    );
  }

  /** Release the delegated drawer controls. */
  dispose() {
    this.events.abort();
  }

  /** @param {string} rail @param {string} openedClass */
  #reflect(rail, openedClass) {
    const button = this.root.querySelector(`[data-rail-action='${rail}']`);
    if (button) {
      button.setAttribute(
        "aria-expanded",
        String(this.root.classList.contains(openedClass)),
      );
    }
  }
}
