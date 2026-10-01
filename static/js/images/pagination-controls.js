/** Own page navigation controls and their delegated actions. */
export class PaginationControls {
  /**
   * @param {HTMLElement} root
   * @param {{onPage: (offset: number) => void}} callbacks
   */
  constructor(root, callbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.events = new AbortController();
    this.root.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const button = target.closest("[data-page-offset]");
        if (
          button instanceof HTMLButtonElement &&
          !button.disabled &&
          button.dataset.pageOffset
        ) {
          this.callbacks.onPage(Number(button.dataset.pageOffset));
        }
      },
      { signal: this.events.signal },
    );
  }

  /** @param {number} total @param {number} offset @param {number} limit */
  render(total, offset, limit) {
    this.root.replaceChildren();
    if (total <= limit && offset === 0) {
      this.root.hidden = true;
      return;
    }
    this.root.hidden = false;
    const previous = pageButton("Zurück", Math.max(0, offset - limit));
    previous.disabled = offset === 0;
    const next = pageButton("Weiter", offset + limit);
    next.disabled = offset + limit >= total;
    const status = document.createElement("span");
    status.className = "pagination-status";
    const first = total === 0 ? 0 : offset + 1;
    const last = Math.min(total, offset + limit);
    status.textContent = `${first}–${last} von ${total}`;
    this.root.append(previous, status, next);
  }

  /** Release the delegated click listener. */
  dispose() {
    this.events.abort();
  }
}

/** @param {string} label @param {number} offset */
function pageButton(label, offset) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "pagination-button";
  button.dataset.pageOffset = String(offset);
  button.textContent = label;
  return button;
}
