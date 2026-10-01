const numberFormatter = new Intl.NumberFormat("de-DE", {
  maximumFractionDigits: 2,
});

/** Render server-computed analytics without reproducing statistics in-browser. */
export class AnalyticsView {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
  }

  /** @param {string} section @param {Record<string, any>} payload */
  render(section, payload) {
    this.root.replaceChildren();
    if (section === "overview") this.#renderOverview(payload);
    else if (section === "scopes") this.#renderScopes(payload);
    else if (section === "parameters") this.#renderParameters(payload);
    else this.#renderCombinations(payload);
  }

  /** Clear rendered report content. */
  clear() {
    this.root.replaceChildren();
  }

  /** @param {Record<string, any>} payload */
  #renderOverview(payload) {
    const layout = document.createElement("div");
    layout.className = "analytics-overview-grid";
    layout.append(
      recommendationGroup("Stabile Empfehlungen", payload.stable),
      recommendationGroup("Vermeiden", payload.avoid),
    );
    this.root.append(layout);
  }

  /** @param {Record<string, any>} payload */
  #renderScopes(payload) {
    const rows = arrayValue(payload.rows).map((row) => [
      scopeKindLabel(row.kind),
      textValue(row.name),
      textValue(row.image_count),
      textValue(row.rating_count),
      decimalValue(row.average_rating),
    ]);
    this.root.append(
      reportTable(
        ["Art", "Scope", "Bilder", "Bewertungen", "Ø Bewertung"],
        rows,
      ),
    );
  }

  /** @param {Record<string, any>} payload */
  #renderParameters(payload) {
    const sections = arrayValue(payload.stats);
    if (!sections.length) {
      this.root.append(emptyMessage("Keine Parameterdaten für diesen Filter."));
      return;
    }
    for (const section of sections) {
      const article = document.createElement("article");
      article.className = "analytics-report-section";
      const title = document.createElement("h2");
      title.textContent = textValue(section.title || section.key);
      const rows = arrayValue(section.rows).map((row) => [
        textValue(row.value),
        textValue(row.n ?? row.sample_count),
        decimalValue(row.avg_rating ?? row.mean_score),
        decimalValue(row.stability_lb05 ?? row.lb05),
      ]);
      article.append(
        title,
        reportTable(["Wert", "Belege", "Ø Bewertung", "Untergrenze"], rows),
      );
      this.root.append(article);
    }
  }

  /** @param {Record<string, any>} payload */
  #renderCombinations(payload) {
    const rows = arrayValue(payload.rows).map((row) => [
      compositionLabel(row.component_names, row.composition_uid),
      textValue(row.image_count),
      textValue(row.rating_count),
      decimalValue(row.average_rating),
    ]);
    this.root.append(
      reportTable(
        ["Kombination", "Bilder", "Bewertungen", "Ø Bewertung"],
        rows,
      ),
    );
  }
}

/** @param {string} title @param {unknown} items */
function recommendationGroup(title, items) {
  const section = document.createElement("section");
  section.className = "analytics-recommendations";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const list = document.createElement("div");
  list.className = "analytics-recommendation-list";
  const rows = arrayValue(items);
  if (!rows.length) list.append(emptyMessage("Keine Einträge."));
  for (const item of rows) {
    const card = document.createElement("article");
    const label = document.createElement("strong");
    label.textContent = textValue(
      item.label || item.combo_key || item.checkpoint,
    );
    const evidence = document.createElement("span");
    evidence.textContent = `${textValue(item.n ?? item.total_rating_count)} Belege · Ø ${decimalValue(item.avg_rating ?? item.average_rating)}`;
    card.append(label, evidence);
    list.append(card);
  }
  section.append(heading, list);
  return section;
}

/** @param {string[]} headings @param {string[][]} rows */
function reportTable(headings, rows) {
  if (!rows.length) return emptyMessage("Keine Daten für diesen Filter.");
  const wrapper = document.createElement("div");
  wrapper.className = "analytics-table-wrap";
  const table = document.createElement("table");
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const heading of headings) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = heading;
    headRow.append(cell);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
  table.append(head, body);
  wrapper.append(table);
  return wrapper;
}

/** @param {string} text */
function emptyMessage(text) {
  const message = document.createElement("p");
  message.className = "analytics-empty";
  message.textContent = text;
  return message;
}

/** @param {unknown} value */
function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

/** @param {unknown} value */
function textValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

/** @param {unknown} value */
function decimalValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? numberFormatter.format(number) : "—";
}

/** @param {unknown} value */
function scopeKindLabel(value) {
  /** @type {Record<string, string>} */
  const labels = {
    character: "Charakter",
    scene: "Szene",
    outfit: "Outfit",
    pose: "Pose",
    expression: "Ausdruck",
    lighting: "Licht",
    modifier: "Modifier",
  };
  const key = String(value || "");
  return labels[key] || textValue(value);
}

/** @param {unknown} names @param {unknown} fallback */
function compositionLabel(names, fallback) {
  const values = arrayValue(names)
    .map(textValue)
    .filter((value) => value !== "—");
  return values.length ? values.join(" · ") : textValue(fallback);
}
