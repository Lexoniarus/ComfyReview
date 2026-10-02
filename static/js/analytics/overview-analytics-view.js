import {
  arrayValue,
  emptyMessage,
  percentValue,
  recordValue,
  reportIntro,
  sectionTitle,
  settingLine,
  textValue,
} from "./analytics-formatters.js";

/** Render the bounded recommendation overview. */
export class OverviewAnalyticsView {
  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    const stable = arrayValue(payload.stable);
    const avoid = arrayValue(payload.avoid);
    const approximate = recordValue(payload.approx);
    root.append(
      reportIntro(
        "Entscheidungshilfe",
        "Beobachtete Evidenz und rechnerische Kandidaten bleiben klar getrennt.",
      ),
      recommendationGroup("Stabile Empfehlungen", stable, "stable"),
      recommendationGroup("Vermeiden", avoid, "avoid"),
      approximationGroup(approximate),
    );
  }
}

/** @param {string} title @param {unknown[]} rows @param {string} tone */
function recommendationGroup(title, rows, tone) {
  const section = document.createElement("section");
  section.className = "analytics-recommendations";
  section.dataset.tone = tone;
  section.append(sectionTitle(title));
  if (!rows.length) section.append(emptyMessage("Keine Einträge."));
  for (const value of rows) {
    const item = recordValue(value);
    const card = document.createElement("article");
    card.textContent = `${textValue(item.label || item.checkpoint)} · ${textValue(item.n)} Belege`;
    section.append(card);
  }
  return section;
}

/** @param {Record<string, any>} approximate */
function approximationGroup(approximate) {
  const section = document.createElement("section");
  section.className = "analytics-approximation";
  section.append(sectionTitle("Rechnerische Kandidaten"));
  const rows = arrayValue(approximate.rows);
  if (!rows.length) {
    section.append(emptyMessage("Keine rechnerischen Kandidaten."));
  }
  for (const value of rows) {
    const item = recordValue(value);
    const card = document.createElement("article");
    const content = document.createElement("span");
    content.textContent = `${settingLine(item)} · ${percentValue(item.pred_success)} prognostiziert`;
    const action = document.createElement("button");
    action.type = "button";
    action.dataset.playgroundIntent = "recommendation";
    action.dataset.recommendation = JSON.stringify(item);
    action.textContent = "Im Generator verwenden";
    card.append(content, action);
    section.append(card);
  }
  return section;
}
