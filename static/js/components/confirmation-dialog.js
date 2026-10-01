/** Own one accessible yes/no dialog and its pending decision. */
export class ConfirmationDialog {
  /** @param {HTMLDialogElement} dialog */
  constructor(dialog) {
    this.dialog = dialog;
    this.message = dialog.querySelector("[data-confirm-message]");
    if (!(this.message instanceof HTMLElement)) {
      throw new Error("confirmation dialog requires a message element");
    }
    this.events = new AbortController();
    /** @type {((confirmed: boolean) => void) | null} */
    this.resolveDecision = null;
    this.dialog.addEventListener("click", (event) => this.#handle(event), {
      signal: this.events.signal,
    });
    this.dialog.addEventListener(
      "cancel",
      (event) => {
        event.preventDefault();
        this.#resolve(false);
      },
      { signal: this.events.signal },
    );
  }

  /** @param {string} message @returns {Promise<boolean>} */
  confirm(message) {
    this.#resolve(false);
    this.message.textContent = message;
    this.dialog.showModal();
    return new Promise((resolve) => {
      this.resolveDecision = resolve;
    });
  }

  /** @returns {boolean} */
  isOpen() {
    return this.dialog.open;
  }

  /** Release listeners and cancel a pending decision. */
  dispose() {
    this.events.abort();
    this.#resolve(false);
  }

  /** @param {Event} event */
  #handle(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const action = target.closest("[data-confirm-result]");
    if (!(action instanceof HTMLElement)) return;
    this.#resolve(action.dataset.confirmResult === "confirm");
  }

  /** @param {boolean} confirmed */
  #resolve(confirmed) {
    if (this.dialog.open) this.dialog.close();
    const resolve = this.resolveDecision;
    this.resolveDecision = null;
    if (resolve) resolve(confirmed);
  }
}
