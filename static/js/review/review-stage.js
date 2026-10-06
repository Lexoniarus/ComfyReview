/** Own candidate presentation and direct review controls. */
export class ReviewStage {
  /**
   * @param {HTMLElement} root
   * @param {{onRate: (rating: number) => void, onDelete: () => void, onExpand: (url: string) => void, createGeneratorActions?: (uid: string) => HTMLElement}} callbacks
   */
  constructor(root, callbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.events = new AbortController();
    /** @type {Record<string, unknown> | null} */
    this.current = null;
    this.root.addEventListener("click", (event) => this.#handleClick(event), {
      signal: this.events.signal,
    });
  }

  /** @param {Record<string, unknown>} image */
  render(image) {
    this.current = image;
    this.root.replaceChildren(
      reviewCard(image, this.callbacks.createGeneratorActions),
    );
  }

  /** @param {string} [message] */
  loading(message = "Nächstes Bild wird geladen …") {
    this.current = null;
    this.#status(message);
  }

  /** Show that no image matches the current scope. */
  empty() {
    this.current = null;
    this.#status("Für diese Auswahl ist kein Bild verfügbar.");
  }

  /** @param {string} message */
  error(message) {
    this.current = null;
    this.#status(
      message || "Das Bild konnte nicht geladen werden.",
      "is-error",
    );
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const button of this.root.querySelectorAll("button")) {
      if (button instanceof HTMLButtonElement) button.disabled = busy;
    }
  }

  /** Release the delegated review controls. */
  dispose() {
    this.events.abort();
  }

  /** @param {Event} event */
  #handleClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const action = target.closest("[data-review-action]");
    if (!(action instanceof HTMLElement)) return;
    if (action.dataset.reviewAction === "rate" && action.dataset.rating) {
      this.callbacks.onRate(Number(action.dataset.rating));
    } else if (action.dataset.reviewAction === "delete") {
      this.callbacks.onDelete();
    } else if (
      action.dataset.reviewAction === "expand" &&
      this.current?.image_url
    ) {
      this.callbacks.onExpand(String(this.current.image_url));
    }
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `review-empty ${className}`.trim();
    status.textContent = message;
    this.root.replaceChildren(status);
  }
}

/** @param {Record<string, unknown>} image @param {((uid: string) => HTMLElement) | undefined} createGeneratorActions */
function reviewCard(image, createGeneratorActions) {
  const card = document.createElement("article");
  card.className = "v2-panel review-card";
  const imageButton = document.createElement("button");
  imageButton.type = "button";
  imageButton.className = "review-image-button";
  imageButton.dataset.reviewAction = "expand";
  imageButton.setAttribute("aria-label", "Bild vergrößern");
  const preview = document.createElement("img");
  preview.src = String(image.image_url || "");
  preview.alt = "Zu bewertendes Bild";
  imageButton.append(preview);
  const scoreRow = document.createElement("div");
  scoreRow.className = "review-score-row";
  scoreRow.setAttribute("aria-label", "Bewertung von 1 bis 10");
  for (let rating = 1; rating <= 10; rating += 1) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "review-score-button";
    button.dataset.reviewAction = "rate";
    button.dataset.rating = String(rating);
    button.textContent = String(rating);
    button.setAttribute("aria-label", `Mit ${rating} von 10 bewerten`);
    scoreRow.append(button);
  }
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "review-delete-button";
  remove.dataset.reviewAction = "delete";
  remove.textContent = "Bild löschen";
  card.append(imageButton, scoreRow, remove);
  const uid = String(image.image_uid || "");
  if (uid && typeof createGeneratorActions === "function") {
    card.append(createGeneratorActions(uid));
  }
  return card;
}
