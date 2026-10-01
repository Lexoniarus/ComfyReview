/** Own pair presentation and Arena controls. */
export class ArenaBoard {
  /**
   * @param {HTMLElement} root
   * @param {{onDecision: (side: "left" | "right") => void, onInspect: (image: Record<string, unknown>) => void, onExpand: (url: string) => void}} callbacks
   */
  constructor(root, callbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.events = new AbortController();
    /** @type {{left: Record<string, unknown>, right: Record<string, unknown>} | null} */
    this.pair = null;
    this.root.addEventListener("click", (event) => this.#handleClick(event), {
      signal: this.events.signal,
    });
  }

  /** @param {{left: Record<string, unknown>, right: Record<string, unknown>}} pair */
  render(pair) {
    this.pair = pair;
    this.root.replaceChildren(
      competitorCard("left", "A", pair.left),
      competitorCard("right", "B", pair.right),
    );
  }

  /** Show pair loading state. */
  loading() {
    this.pair = null;
    this.#status("Arena-Paar wird geladen …");
  }

  /** Show an exhausted Arena pool. */
  empty() {
    this.pair = null;
    this.#status("Für diese Auswahl sind alle Paarungen abgeschlossen.");
  }

  /** @param {string} message */
  error(message) {
    this.pair = null;
    this.#status(
      message || "Das Arena-Paar konnte nicht geladen werden.",
      "is-error",
    );
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const button of this.root.querySelectorAll("button")) {
      if (button instanceof HTMLButtonElement) button.disabled = busy;
    }
  }

  /** Release delegated pair controls. */
  dispose() {
    this.events.abort();
  }

  /** @param {Event} event */
  #handleClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const action = target.closest("[data-arena-action]");
    if (!(action instanceof HTMLElement) || !this.pair) return;
    const side = action.dataset.side === "right" ? "right" : "left";
    const image = this.pair[side];
    if (action.dataset.arenaAction === "decide") {
      this.callbacks.onDecision(side);
    } else if (action.dataset.arenaAction === "inspect") {
      this.callbacks.onInspect(image);
    } else if (action.dataset.arenaAction === "expand" && image.image_url) {
      this.callbacks.onExpand(String(image.image_url));
    }
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `arena-empty ${className}`.trim();
    status.textContent = message;
    this.root.replaceChildren(status);
  }
}

/** @param {"left" | "right"} side @param {string} label @param {Record<string, unknown>} image */
function competitorCard(side, label, image) {
  const card = document.createElement("article");
  card.className = "v2-panel arena-card";
  const imageButton = document.createElement("button");
  imageButton.type = "button";
  imageButton.className = "arena-image-button";
  imageButton.dataset.arenaAction = "expand";
  imageButton.dataset.side = side;
  imageButton.setAttribute("aria-label", `Bild ${label} vergrößern`);
  const preview = document.createElement("img");
  preview.src = String(image.image_url || "");
  preview.alt = `Arena-Bild ${label}`;
  imageButton.append(preview);
  const actions = document.createElement("div");
  actions.className = "arena-card-actions";
  const decide = document.createElement("button");
  decide.type = "button";
  decide.className = "arena-decision";
  decide.dataset.arenaAction = "decide";
  decide.dataset.side = side;
  decide.textContent = `Bild ${label} gewinnt`;
  const inspect = document.createElement("button");
  inspect.type = "button";
  inspect.className = "arena-inspect";
  inspect.dataset.arenaAction = "inspect";
  inspect.dataset.side = side;
  inspect.textContent = "Details";
  actions.append(decide, inspect);
  card.append(imageButton, actions);
  return card;
}
