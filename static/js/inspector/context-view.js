/** Render canonical image identity, rating, classification, and scopes. */
export class ContextView {
  constructor() {
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-context";
  }

  /** @param {Record<string, any>} image */
  render(image) {
    this.element.replaceChildren();
    const preview = document.createElement("img");
    preview.className = "inspector-preview";
    preview.src = String(image.image_url || "");
    preview.alt = "Ausgewähltes Bild";

    const facts = document.createElement("div");
    facts.className = "inspector-facts";
    facts.append(
      detailRow("Bild-UID", image.image_uid),
      detailRow("Generation", image.generation_uid),
      detailRow(
        "Klassifikation",
        image.classification === "unclassified"
          ? "Unklassifiziert"
          : "Klassifiziert",
      ),
      detailRow("Bewertung", reviewLabel(image.review_summary)),
    );

    const scopes = document.createElement("div");
    scopes.className = "inspector-scopes scope-chip-row";
    for (const scope of image.scopes || []) {
      const chip = document.createElement("span");
      chip.className = "scope-chip";
      chip.dataset.scopeKind = String(scope.kind || "");
      chip.textContent = String(scope.name || "");
      scopes.append(chip);
    }
    for (const lora of image.loras || []) {
      const chip = document.createElement("span");
      chip.className = "scope-chip";
      chip.dataset.scopeKind = "lora";
      chip.textContent = `LoRA · ${String(lora.provider_name || lora.lora_uid || "Unbekannt")}`;
      chip.title = `Model ${formatWeight(lora.model_strength)} · CLIP ${formatWeight(lora.clip_strength)}`;
      scopes.append(chip);
    }
    if (!scopes.children.length) {
      const empty = document.createElement("p");
      empty.className = "inspector-empty";
      empty.textContent = "Keine kanonischen Scopes zugeordnet.";
      scopes.append(empty);
    }
    this.element.append(preview, facts, scopes);
  }
}

/** @param {unknown} value */
function formatWeight(value) {
  return Number(value || 0)
    .toFixed(2)
    .replace(".", ",");
}

/** @param {unknown} summary */
function reviewLabel(summary) {
  const review =
    summary && typeof summary === "object"
      ? /** @type {Record<string, any>} */ (summary)
      : {};
  return typeof review.average_rating === "number"
    ? `Ø ${review.average_rating.toFixed(1).replace(".", ",")} / 10 · ${Number(review.rating_count || 0)}×`
    : "Noch unbewertet";
}

/** @param {string} label @param {unknown} value */
function detailRow(label, value) {
  const row = document.createElement("dl");
  row.className = "inspector-detail";
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = String(value || "—");
  row.append(term, description);
  return row;
}
