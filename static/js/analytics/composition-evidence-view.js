import {
  arrayValue,
  decimalValue,
  emptyMessage,
  recordValue,
  reportIntro,
  textValue,
} from "./analytics-formatters.js";
import { createBestImagePromptAction } from "./best-image-prompt-action.js";

/** Render actually used prompt-composition evidence. */
export class CompositionEvidenceView {
  /** @param {{images: import("./evidence-image-strip.js").EvidenceImageStrip, setups: import("./render-setup-view.js").RenderSetupView}} dependencies */
  constructor(dependencies) {
    this.images = dependencies.images;
    this.setups = dependencies.setups;
    this.collection = document.createElement("div");
  }

  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    this.collection.replaceChildren();
    this.collection.className = "analytics-composition-grid media-card-grid";
    root.append(
      reportIntro(
        "Prompt-Kombinationen",
        "Nur tatsächlich verwendete kanonische Fakten werden gezeigt; mögliche Kreuzprodukte entstehen nicht.",
      ),
      this.collection,
    );
    this.append(payload.items);
    if (!this.collection.children.length) {
      this.collection.append(
        emptyMessage("Keine Kombinationen für diesen Filter."),
      );
    }
  }

  /** @param {unknown} values */
  append(values) {
    for (const value of arrayValue(values)) {
      this.collection.append(this.#compositionCard(value));
    }
  }

  /** @param {string} compositionUid @param {Record<string, any>} payload */
  renderSetups(compositionUid, payload) {
    const card = this.collection.querySelector(
      `[data-composition-uid="${CSS.escape(compositionUid)}"]`,
    );
    if (!(card instanceof HTMLElement)) return;
    const existing = card.querySelector("[data-composition-setups]");
    const details = document.createElement("section");
    details.dataset.compositionSetups = "";
    details.className = "analytics-composition-setups";
    const title = document.createElement("h3");
    title.textContent = "Beobachtete Render-Setups";
    details.append(title);
    const rows = arrayValue(payload.rows);
    if (!rows.length) details.append(emptyMessage("Keine technischen Setups."));
    for (const row of rows) details.append(this.setups.render(row));
    if (existing) existing.replaceWith(details);
    else card.append(details);
  }

  /** @param {unknown} value */
  #compositionCard(value) {
    const row = recordValue(value);
    const card = document.createElement("article");
    card.className = "analytics-composition-card media-card";
    card.dataset.compositionUid = String(row.composition_uid || "");
    card.dataset.itemKey = String(row.composition_uid || "");
    card.append(this.images.render(row.best_images, "Prompt-Kombination"));
    const scopes = document.createElement("div");
    scopes.className = "analytics-composition-scopes";
    for (const name of arrayValue(row.component_names)) {
      const chip = document.createElement("span");
      chip.textContent = textValue(name);
      scopes.append(chip);
    }
    if (!scopes.children.length) {
      const identity = document.createElement("span");
      identity.textContent = textValue(row.composition_uid);
      scopes.append(identity);
    }
    const evidence = document.createElement("p");
    evidence.className = "analytics-evidence";
    evidence.textContent = `${textValue(row.image_count)} Bilder · ${textValue(row.rating_count)} Bewertungen · Ø ${decimalValue(row.average_rating)} / 10`;
    const actions = document.createElement("div");
    actions.className = "analytics-card-actions";
    const use = createBestImagePromptAction(row.best_images);
    const details = document.createElement("button");
    details.type = "button";
    details.dataset.compositionDetails = String(row.composition_uid || "");
    details.textContent = "Technische Setups anzeigen";
    actions.append(use, details);
    card.append(scopes, evidence, actions);
    return card;
  }
}
