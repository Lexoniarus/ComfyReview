import {
  decimalValue,
  emptyMessage,
  recordValue,
  reportIntro,
  scopeKindLabels,
  textValue,
} from "./analytics-formatters.js";

/** Render one focused canonical scope collection. */
export class ScopeEvidenceView {
  /** @param {{images: import("./evidence-image-strip.js").EvidenceImageStrip}} dependencies */
  constructor(dependencies) {
    this.images = dependencies.images;
    this.grid = document.createElement("div");
    this.grid.className = "analytics-scope-grid";
  }

  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    this.grid.replaceChildren();
    const kind = String(payload.kind || "character");
    root.append(
      reportIntro(
        "Scope-Evidenz",
        "Kanonische Prompt-Komponenten mit realen Bildbeispielen.",
      ),
      scopeNavigation(kind),
      this.grid,
    );
    this.append(payload.items);
    if (!this.grid.children.length) {
      this.grid.append(emptyMessage("Keine Scopes für diesen Filter."));
    }
  }

  /** @param {unknown} values */
  append(values) {
    for (const value of Array.isArray(values) ? values : []) {
      const row = recordValue(value);
      const card = document.createElement("article");
      card.className = "analytics-scope-card";
      card.dataset.kind = String(row.kind || "modifier");
      card.dataset.itemKey = String(row.component_uid || "");
      const title = document.createElement("h3");
      title.textContent = textValue(row.name);
      const action = document.createElement("button");
      action.type = "button";
      action.className = "secondary-button analytics-use-button";
      action.dataset.playgroundIntent = "scope";
      action.dataset.componentUid = String(row.component_uid || "");
      action.textContent = "Im Generator verwenden";
      card.append(this.images.render(row.best_images, String(row.name)), title);
      if (row.archived) {
        const archived = document.createElement("span");
        archived.className = "analytics-archived";
        archived.textContent = "Archiviert";
        card.append(archived);
      }
      const evidence = document.createElement("p");
      evidence.className = "analytics-evidence";
      evidence.textContent = `${textValue(row.image_count)} Bilder · ${textValue(row.rating_count)} Bewertungen · Ø ${decimalValue(row.average_rating)} / 10`;
      card.append(evidence, action);
      this.grid.append(card);
    }
  }
}

/** @param {string} selectedKind */
function scopeNavigation(selectedKind) {
  const navigation = document.createElement("nav");
  navigation.className = "analytics-subtabs";
  navigation.setAttribute("aria-label", "Scope-Art");
  for (const [kind, label] of scopeKindLabels) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.dataset.analyticsScopeKind = kind;
    button.setAttribute("aria-pressed", String(kind === selectedKind));
    navigation.append(button);
  }
  return navigation;
}
