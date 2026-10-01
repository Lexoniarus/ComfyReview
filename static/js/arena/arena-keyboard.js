/** Own left/right decision shortcuts for one Arena surface. */
export class ArenaKeyboard {
  /** @param {Document} documentRoot @param {{onDecision: (side: "left" | "right") => void}} callbacks */
  constructor(documentRoot, callbacks) {
    this.events = new AbortController();
    documentRoot.addEventListener(
      "keydown",
      (event) => {
        if (isBlocked(event)) return;
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          callbacks.onDecision(event.key === "ArrowLeft" ? "left" : "right");
        }
      },
      { signal: this.events.signal },
    );
  }

  /** Release the global keyboard listener. */
  dispose() {
    this.events.abort();
  }
}

/** @param {KeyboardEvent} event */
function isBlocked(event) {
  if (
    event.defaultPrevented ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey
  ) {
    return true;
  }
  const target = event.target;
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable ||
      ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}
