/** Own the shared image-inspector presentation state. */
export class ImageInspector {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
  }

  /** @param {Record<string, unknown>} image */
  render(image) {
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
    this.root.append(
      heading,
      preview,
      identity,
      generation,
      score,
      scopes,
      promptDetails,
    );
  }

  /** Show the inspector's initial state. */
  empty() {
    this.#status("Wähle ein Bild aus, um Details zu sehen.");
  }

  /** Show a loading state for an incoming image context. */
  loading() {
    this.#status("Bilddetails werden geladen …");
  }

  /** @param {string} message */
  error(message) {
    this.#status(
      message || "Bilddetails konnten nicht geladen werden.",
      "is-error",
    );
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `inspector-status ${className}`.trim();
    status.textContent = message;
    this.root.replaceChildren(status);
  }
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
