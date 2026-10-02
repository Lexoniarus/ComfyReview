import {
  arrayValue,
  decimalValue,
  emptyMessage,
  parameterLabels,
  percentValue,
  recordValue,
  reportIntro,
  sectionTitle,
  settingLine,
  textValue,
} from "./analytics-formatters.js";

/** Render calculated and observed render-parameter evidence. */
export class ParameterEvidenceView {
  /** @param {{images: import("./evidence-image-strip.js").EvidenceImageStrip, setups: import("./render-setup-view.js").RenderSetupView}} dependencies */
  constructor(dependencies) {
    this.images = dependencies.images;
    this.setups = dependencies.setups;
    this.collection = document.createElement("div");
  }

  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    this.collection.replaceChildren();
    const view = String(payload.view || "summary");
    const parameter = String(payload.parameter || "");
    root.append(
      reportIntro(
        "Renderparameter",
        "Rechnerische Empfehlungen und gemeinsam beobachtete Setups bleiben getrennt.",
      ),
      parameterNavigation(view, parameter),
    );
    if (view === "values") {
      this.collection.className = "analytics-parameter-grid";
      root.append(
        sectionTitle(parameterLabels.get(parameter) || "Werte"),
        this.collection,
      );
      this.append(payload.items, view);
      if (!this.collection.children.length) {
        this.collection.append(
          emptyMessage("Keine Werte für diesen Parameter."),
        );
      }
      return;
    }
    root.append(
      sectionTitle("Rechnerische Empfehlung · nicht gemeinsam getestet"),
      recommendationGrid(payload.recommendations),
      sectionTitle("Beobachtete vollständige Setups"),
    );
    this.collection.className = "analytics-tested-list";
    root.append(this.collection);
    this.append(payload.items, view);
    if (!this.collection.children.length) {
      this.collection.append(emptyMessage("Keine beobachteten Setups."));
    }
  }

  /** @param {unknown} values @param {string} view */
  append(values, view = "summary") {
    for (const value of arrayValue(values)) {
      this.collection.append(
        view === "values"
          ? this.#parameterCard(value)
          : this.setups.render(value),
      );
    }
  }

  /** @param {unknown} value */
  #parameterCard(value) {
    const row = recordValue(value);
    const card = document.createElement("article");
    card.className = "analytics-parameter-card";
    card.dataset.itemKey = `${textValue(row.parameter)}:${textValue(row.value)}`;
    const content = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = textValue(row.value);
    const evidence = document.createElement("span");
    evidence.textContent = `${textValue(row.sample_count)} Belege · Ø ${decimalValue(row.average_rating)} / 10`;
    const confidence = document.createElement("span");
    confidence.textContent = `Erwartet ${percentValue(row.expected_success_rate)} · Untergrenze ${percentValue(row.lower_bound)}`;
    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary-button analytics-use-button";
    action.dataset.playgroundIntent = "parameter";
    action.dataset.parameter = String(row.parameter || "");
    action.dataset.value = String(row.value || "");
    action.textContent = "Im Generator verwenden";
    content.append(name, evidence, confidence, action);
    card.append(
      content,
      this.images.render(row.best_images, String(row.value)),
    );
    return card;
  }
}

/** @param {string} selectedView @param {string} selectedParameter */
function parameterNavigation(selectedView, selectedParameter) {
  const navigation = document.createElement("nav");
  navigation.className = "analytics-subtabs";
  navigation.setAttribute("aria-label", "Parameteransicht");
  navigation.append(
    viewButton("Übersicht", "summary", "", selectedView, selectedParameter),
  );
  for (const [parameter, label] of parameterLabels) {
    navigation.append(
      viewButton(label, "values", parameter, selectedView, selectedParameter),
    );
  }
  return navigation;
}

/** @param {string} label @param {string} view @param {string} parameter @param {string} selectedView @param {string} selectedParameter */
function viewButton(label, view, parameter, selectedView, selectedParameter) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.dataset.analyticsView = view;
  if (parameter) button.dataset.analyticsParameter = parameter;
  button.setAttribute(
    "aria-pressed",
    String(view === selectedView && parameter === selectedParameter),
  );
  return button;
}

/** @param {unknown} values */
function recommendationGrid(values) {
  const rows = arrayValue(values);
  if (!rows.length) return emptyMessage("Keine rechnerischen Empfehlungen.");
  const grid = document.createElement("div");
  grid.className = "analytics-best-grid";
  for (const value of rows) {
    const item = recordValue(value);
    const card = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = textValue(item.checkpoint);
    const settings = document.createElement("span");
    settings.textContent = settingLine(item);
    const score = document.createElement("span");
    score.textContent = `Prognose ${percentValue(item.score)} · Checkpoint-Untergrenze ${percentValue(item.checkpoint_lower_bound)}`;
    const action = document.createElement("button");
    action.type = "button";
    action.className = "secondary-button analytics-use-button";
    action.dataset.playgroundIntent = "recommendation";
    action.dataset.recommendation = JSON.stringify(item);
    action.textContent = "Im Generator verwenden";
    card.append(title, settings, score, action);
    grid.append(card);
  }
  return grid;
}
