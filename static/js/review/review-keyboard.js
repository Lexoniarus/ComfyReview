/** Own keyboard shortcuts for one review surface. */
export class ReviewKeyboard {
  /**
   * @param {Document} documentRoot
   * @param {{onRate: (rating: number) => void, onDelete: () => void, isDialogOpen: () => boolean}} callbacks
   */
  constructor(documentRoot, callbacks) {
    this.documentRoot = documentRoot;
    this.callbacks = callbacks;
    this.events = new AbortController();
    this.documentRoot.addEventListener(
      "keydown",
      (event) => this.#handle(event),
      { signal: this.events.signal },
    );
  }

  /** Release the global keyboard listener. */
  dispose() {
    this.events.abort();
  }

  /** @param {KeyboardEvent} event */
  #handle(event) {
    if (
      event.defaultPrevented ||
      event.ctrlKey ||
      event.metaKey ||
      event.altKey ||
      this.callbacks.isDialogOpen() ||
      isEditing(event.target)
    ) {
      return;
    }
    if (event.key === "Delete") {
      event.preventDefault();
      this.callbacks.onDelete();
    } else if (event.key >= "1" && event.key <= "9") {
      event.preventDefault();
      this.callbacks.onRate(Number(event.key));
    } else if (event.key === "0") {
      event.preventDefault();
      this.callbacks.onRate(10);
    }
  }
}

/** @param {EventTarget | null} target */
function isEditing(target) {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}
