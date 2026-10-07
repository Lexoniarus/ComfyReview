import { recordValue, reportIntro, textValue } from "./analytics-formatters.js";
import { AnalyticsCardRail } from "./analytics-card-rail.js";

/** Render coverage and diagnostics without mixing in recommendations. */
export class OverviewAnalyticsView {
  constructor() {
    this.metrics = new AnalyticsCardRail("analytics-overview-card-track");
    this.modeled = new AnalyticsCardRail("analytics-overview-card-track");
    this.geometry = new AnalyticsCardRail("analytics-overview-card-track");
  }

  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    root.append(
      reportIntro(
        "Datenabdeckung",
        "Die Übersicht zeigt, was die kanonischen Daten tatsächlich abdecken. Empfehlungen stehen ausschließlich in der Render-Analyse.",
      ),
      overviewSection(
        "Abdeckung",
        "Was in der kanonischen Datenbasis tatsächlich vorhanden ist.",
        this.metrics,
        metricCards(payload),
      ),
      overviewSection(
        "Modellierbare Einzelwerte",
        "Werte mit mindestens drei unabhängigen Bildern; fehlende Variation bleibt neutral.",
        this.modeled,
        modeledValueCards(payload.modeled_value_counts),
      ),
      overviewSection(
        "Deskriptive Ausgabegeometrie",
        "Format und Auflösung beschreiben vorhandene Bilder; sie sind keine Sampler-Empfehlung.",
        this.geometry,
        geometryValueCards(payload.geometry_value_counts),
      ),
    );
  }

  /** Release every owned carousel. */
  dispose() {
    this.metrics.dispose();
    this.modeled.dispose();
    this.geometry.dispose();
  }
}

/** @param {string} titleText @param {string} descriptionText @param {AnalyticsCardRail} rail @param {HTMLElement[]} cards */
function overviewSection(titleText, descriptionText, rail, cards) {
  const section = document.createElement("section");
  section.className = "analytics-overview-section";
  const title = document.createElement("h2");
  title.textContent = titleText;
  const description = document.createElement("p");
  description.textContent = descriptionText;
  rail.clear();
  rail.append(...cards);
  section.append(title, description, rail.element);
  return section;
}

/** @param {Record<string, any>} payload */
function metricCards(payload) {
  const cards = [];
  for (const [label, value] of [
    ["Aktive Bilder", payload.active_image_count],
    ["Bewertete Bilder", payload.rated_image_count],
    ["Beobachtete Render-Setups", payload.observed_setup_count],
    ["Davon ausreichend gesichtet", payload.stable_setup_count],
    ["Prompt-verknüpft", payload.prompt_linked_image_count],
    ["Prompt-Abdeckung fehlt", payload.unlinked_prompt_image_count],
    ["Legacy-Bilder", payload.legacy_image_count],
    ["Geometrie projiziert", payload.geometry_projected_count],
  ]) {
    const wrapper = document.createElement("article");
    wrapper.className = "analytics-overview-card";
    const term = document.createElement("span");
    term.textContent = label;
    const description = document.createElement("strong");
    description.textContent = textValue(value);
    wrapper.append(term, description);
    cards.push(wrapper);
  }
  return cards;
}

/** @param {unknown} values */
function modeledValueCards(values) {
  const cards = [];
  const rows = recordValue(values);
  for (const [key, value] of Object.entries(rows)) {
    cards.push(overviewValueCard(label(key), textValue(value), "Werte"));
  }
  return cards;
}

/** @param {unknown} values */
function geometryValueCards(values) {
  return (Array.isArray(values) ? values : []).map((value) => {
    const row = recordValue(value);
    return overviewValueCard(
      `${label(String(row.dimension || ""))} ${textValue(row.value)}`,
      textValue(row.image_count),
      "Bilder",
    );
  });
}

/** @param {string} title @param {string} value @param {string} unit */
function overviewValueCard(title, value, unit) {
  const card = document.createElement("article");
  card.className = "analytics-overview-card";
  const heading = document.createElement("span");
  heading.textContent = title;
  const amount = document.createElement("strong");
  amount.textContent = value;
  const suffix = document.createElement("small");
  suffix.textContent = unit;
  card.append(heading, amount, suffix);
  return card;
}

/** @param {string} key */
function label(key) {
  return (
    {
      checkpoint: "Checkpoint",
      sampler: "Sampler",
      scheduler: "Scheduler",
      steps: "Steps",
      cfg: "CFG",
      denoise: "Denoise",
      aspect_format: "Format",
      resolution_class: "Auflösungsklasse",
    }[key] || key
  );
}
