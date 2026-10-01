/** Own the shared image-inspector presentation state. */
export class ImageInspector {
  /**
   * @param {HTMLElement} root
   * @param {{onCuration?: (imageUid: string, setKey: string) => void}} [actions]
   */
  constructor(root, actions = {}) {
    this.root = root;
    this.onCuration = actions.onCuration || (() => {});
    this.events = new AbortController();
    /** @type {Record<string, unknown> | null} */
    this.currentImage = null;
    /** @type {string[]} */
    this.curationSetKeys = [];
    this.isCurationBusy = false;
    this.curationError = "";
    this.root.addEventListener("click", (event) => this.#handleAction(event), {
      signal: this.events.signal,
    });
  }

  /** @param {Record<string, unknown>} image */
  render(image) {
    this.currentImage = image;
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "v2-panel-heading";
    heading.textContent = "Bilddetails";
    const preview = document.createElement("img");
    preview.className = "inspector-preview";
    preview.src = String(image.image_url || "");
    preview.alt = "Ausgewähltes Bild";
    const identity = detailRow("Bild-UID", String(image.image_uid || ""));
    const generation = detailRow(
      "Generation",
      String(image.generation_uid || ""),
    );
    const review = /** @type {Record<string, unknown>} */ (
      image.review_summary || {}
    );
    const score = detailRow(
      "Bewertung",
      typeof review.average_rating === "number"
        ? `Ø ${review.average_rating.toFixed(1).replace(".", ",")} / 10 · ${Number(review.rating_count || 0)}×`
        : "Noch unbewertet",
    );
    const scopes = document.createElement("div");
    scopes.className = "inspector-scopes scope-chip-row";
    for (const scope of /** @type {Array<Record<string, unknown>>} */ (
      image.scopes || []
    )) {
      const chip = document.createElement("span");
      chip.className = "scope-chip";
      chip.dataset.scopeKind = String(scope.kind || "");
      chip.textContent = String(scope.name || "");
      scopes.append(chip);
    }
    const prompt = /** @type {Record<string, unknown>} */ (
      image.prompt_snapshot || {}
    );
    const promptDetails = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = prompt.draft_overridden
      ? "Prompt · Draft-Override"
      : "Prompt";
    const positive = document.createElement("p");
    positive.textContent = String(prompt.positive || "");
    const negative = document.createElement("p");
    negative.className = "muted";
    negative.textContent = String(prompt.negative || "");
    promptDetails.append(summary, positive, negative);
    const curation = this.#curationControls(image);
    this.root.append(
      heading,
      preview,
      identity,
      generation,
      score,
      scopes,
      curation,
      promptDetails,
    );
  }

  /** @param {string[]} setKeys */
  setCurationOptions(setKeys) {
    this.curationSetKeys = [...setKeys];
    if (this.currentImage) this.render(this.currentImage);
  }

  /** @param {boolean} busy */
  setCurationBusy(busy) {
    this.isCurationBusy = busy;
    const select = this.root.querySelector("[data-curation-set]");
    const button = this.root.querySelector("[data-curation-assign]");
    if (select instanceof HTMLSelectElement) select.disabled = busy;
    if (button instanceof HTMLButtonElement) {
      const hasSelection =
        select instanceof HTMLSelectElement && Boolean(select.value);
      button.disabled = busy || !hasSelection;
    }
  }

  /** @param {string} message */
  showCurationError(message) {
    this.curationError = message;
    const status = this.root.querySelector("[data-curation-status]");
    if (status instanceof HTMLElement) {
      status.textContent = message;
      status.hidden = !message;
    }
  }

  /** Show the inspector's initial state. */
  empty() {
    this.currentImage = null;
    this.#status("Wähle ein Bild aus, um Details zu sehen.");
  }

  /** Show a loading state for an incoming image context. */
  loading() {
    this.currentImage = null;
    this.#status("Bilddetails werden geladen …");
  }

  /** @param {string} message */
  error(message) {
    this.currentImage = null;
    this.#status(
      message || "Bilddetails konnten nicht geladen werden.",
      "is-error",
    );
  }

  /** Release the inspector's delegated event listener. */
  dispose() {
    this.events.abort();
  }

  /** @param {Record<string, unknown>} image */
  #curationControls(image) {
    const section = document.createElement("section");
    section.className = "inspector-curation";
    const heading = document.createElement("h3");
    heading.textContent = "Curation";
    const controls = document.createElement("div");
    controls.className = "inspector-curation-controls";
    const select = document.createElement("select");
    select.dataset.curationSet = "";
    select.setAttribute("aria-label", "Curation-Set");
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Set auswählen";
    select.append(placeholder);
    for (const setKey of this.curationSetKeys) {
      const option = document.createElement("option");
      option.value = setKey;
      option.textContent = curationLabel(setKey);
      select.append(option);
    }
    const current = /** @type {Record<string, unknown>} */ (
      image.curation || {}
    );
    select.value = String(current.set_key || "");
    select.disabled = this.isCurationBusy;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.dataset.curationAssign = "";
    button.textContent = "Zuweisen";
    button.disabled = this.isCurationBusy || !select.value;
    select.addEventListener(
      "change",
      () => {
        button.disabled = this.isCurationBusy || !select.value;
      },
      { signal: this.events.signal },
    );
    const status = document.createElement("p");
    status.className = "inspector-curation-status is-error";
    status.dataset.curationStatus = "";
    status.textContent = this.curationError;
    status.hidden = !this.curationError;
    controls.append(select, button);
    section.append(heading, controls, status);
    return section;
  }

  /** @param {Event} event */
  #handleAction(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (!target.closest("[data-curation-assign]")) return;
    const select = this.root.querySelector("[data-curation-set]");
    const imageUid = String(this.currentImage?.image_uid || "");
    if (!(select instanceof HTMLSelectElement) || !imageUid || !select.value) {
      return;
    }
    this.onCuration(imageUid, select.value);
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `inspector-status ${className}`.trim();
    status.textContent = message;
    this.root.replaceChildren(status);
  }
}

/** @param {string} setKey */
function curationLabel(setKey) {
  /** @type {Record<string, string>} */
  const labels = {
    character_face: "Charakter · Gesicht",
    character_body: "Charakter · Körper",
    scene: "Szene",
    outfit: "Outfit",
    pose: "Pose",
    expression: "Ausdruck",
  };
  return labels[setKey] || setKey.replaceAll("_", " ");
}

/** @param {string} label @param {string} value */
function detailRow(label, value) {
  const row = document.createElement("dl");
  row.className = "inspector-detail";
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value;
  row.append(term, description);
  return row;
}
