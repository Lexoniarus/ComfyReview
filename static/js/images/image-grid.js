/** Own the ranked image-grid DOM and selection events. */
export class ImageGrid {
  /**
   * @param {HTMLElement} root
   * @param {{onSelect: (uid: string) => void, onExpand: (uid: string, url: string) => void}} callbacks
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
        const action = target.closest("[data-image-action]");
        if (!(action instanceof HTMLElement)) return;
        const uid = action.dataset.imageUid || "";
        if (action.dataset.imageAction === "expand") {
          this.callbacks.onExpand(uid, action.dataset.imageUrl || "");
        } else if (uid) {
          this.callbacks.onSelect(uid);
        }
      },
      { signal: this.events.signal },
    );
  }

  /** @param {Array<Record<string, unknown>>} items @param {number} offset */
  render(items, offset) {
    this.root.replaceChildren();
    if (items.length === 0) {
      this.#status("Keine Bilder für diese Auswahl gefunden.");
      return;
    }
    items.forEach((item, index) =>
      this.root.append(imageCard(item, offset + index + 1)),
    );
  }

  /** Show a loading state without retaining stale cards. */
  loading() {
    this.root.replaceChildren();
    this.#status("Bilder werden geladen …", "is-loading");
  }

  /** @param {string} message */
  error(message) {
    this.root.replaceChildren();
    this.#status(message || "Bilder konnten nicht geladen werden.", "is-error");
  }

  /** Release every DOM listener owned by this component. */
  dispose() {
    this.events.abort();
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `image-grid-status ${className}`.trim();
    status.textContent = message;
    this.root.append(status);
  }
}

/** @param {Record<string, unknown>} item @param {number} rank */
function imageCard(item, rank) {
  const article = document.createElement("article");
  article.className = "image-card";
  const uid = String(item.image_uid || "");
  const url = String(item.image_url || "");
  const imageButton = document.createElement("button");
  imageButton.type = "button";
  imageButton.className = "image-card-media";
  imageButton.dataset.imageAction = "select";
  imageButton.dataset.imageUid = uid;
  const image = document.createElement("img");
  image.src = url;
  image.alt = `Bild ${rank}`;
  image.loading = "lazy";
  imageButton.append(image);

  const body = document.createElement("div");
  body.className = "image-card-body";
  const top = document.createElement("div");
  top.className = "image-card-topline";
  const rankLabel = document.createElement("strong");
  rankLabel.textContent = `#${rank}`;
  const review = /** @type {Record<string, unknown>} */ (
    item.review_summary || {}
  );
  const average =
    typeof review.average_rating === "number" ? review.average_rating : null;
  const rating = document.createElement("span");
  rating.textContent =
    average === null
      ? "Noch unbewertet"
      : `Ø ${average.toFixed(1).replace(".", ",")} / 10`;
  top.append(rankLabel, rating);
  const count = document.createElement("span");
  count.className = "image-card-count";
  count.textContent = `${Number(review.rating_count || 0)} Bewertungen`;
  const scopes = document.createElement("div");
  scopes.className = "scope-chip-row";
  for (const scope of /** @type {Array<Record<string, unknown>>} */ (
    item.scopes || []
  ).slice(0, 3)) {
    const chip = document.createElement("span");
    chip.className = "scope-chip";
    chip.dataset.scopeKind = String(scope.kind || "");
    chip.textContent = String(scope.name || "");
    scopes.append(chip);
  }
  const expand = document.createElement("button");
  expand.type = "button";
  expand.className = "icon-button";
  expand.dataset.imageAction = "expand";
  expand.dataset.imageUid = uid;
  expand.dataset.imageUrl = url;
  expand.setAttribute("aria-label", "Bild vergrößern");
  expand.textContent = "↗";
  body.append(top, count, scopes, expand);
  article.append(imageButton, body);
  return article;
}
