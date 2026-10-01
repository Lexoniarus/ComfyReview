const numberFormatter = new Intl.NumberFormat("de-DE", {
  maximumFractionDigits: 2,
});

const scopeKindOrder = [
  "character",
  "scene",
  "outfit",
  "pose",
  "expression",
  "lighting",
  "modifier",
];

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
    const stable = arrayValue(payload.stable);
    const avoid = arrayValue(payload.avoid);
    const approximate = recordValue(payload.approx);
    const base = recordValue(approximate.base);
    this.root.append(
      reportIntro(
        "Entscheidungshilfe",
        "Beobachtete Einstellungen, konservative Evidenz und rechnerische Kandidaten bleiben klar getrennt.",
      ),
      metricStrip([
        ["Stabil", stable.length],
        ["Vermeiden", avoid.length],
        ["Beobachtungen", base.n],
        ["Basis-Erfolg", percentValue(base.exp)],
      ]),
      calculationExample(payload, stable[0]),
    );

    const layout = document.createElement("div");
    layout.className = "analytics-overview-grid";
    layout.append(
      recommendationGroup("Stabile Empfehlungen", stable, "stable"),
      recommendationGroup("Vermeiden", avoid, "avoid"),
    );
    this.root.append(layout, approximationGroup(approximate));
  }

  /** @param {Record<string, any>} payload */
  #renderScopes(payload) {
    const rows = arrayValue(payload.rows);
    this.root.append(
      reportIntro(
        "Scope-Evidenz",
        "Jede Karte steht für eine kanonische Prompt-Komponente. Bilder zeigen die am besten bewerteten realen Beispiele dieses Scopes.",
      ),
    );
    if (!rows.length) {
      this.root.append(emptyMessage("Keine Scopes für diesen Filter."));
      return;
    }
    for (const kind of scopeKindOrder) {
      const kindRows = rows.filter((row) => String(row.kind) === kind);
      if (!kindRows.length) continue;
      const section = document.createElement("section");
      section.className = "analytics-scope-section";
      const heading = document.createElement("h2");
      heading.textContent = scopeKindLabel(kind);
      const grid = document.createElement("div");
      grid.className = "analytics-scope-grid";
      for (const row of kindRows) grid.append(scopeCard(row));
      section.append(heading, grid);
      this.root.append(section);
    }
  }

  /** @param {Record<string, any>} payload */
  #renderParameters(payload) {
    const sections = arrayValue(payload.stats);
    this.root.append(
      reportIntro(
        "Renderparameter",
        "Berechnete Vorschläge und tatsächlich beobachtete Werte werden getrennt dargestellt. Beispielbilder bleiben an den realen Beobachtungen.",
      ),
      bestCaseSection(arrayValue(payload.best)),
    );
    if (!sections.length) {
      this.root.append(emptyMessage("Keine Parameterdaten für diesen Filter."));
      return;
    }
    for (const section of sections) {
      const article = document.createElement("article");
      article.className = "analytics-report-section";
      const title = document.createElement("h2");
      title.textContent = textValue(section.title || section.key);
      const grid = document.createElement("div");
      grid.className = "analytics-parameter-grid";
      for (const row of arrayValue(section.rows)) {
        grid.append(parameterCard(row));
      }
      article.append(title, grid);
      this.root.append(article);
    }
  }

  /** @param {Record<string, any>} payload */
  #renderCombinations(payload) {
    const rows = arrayValue(payload.rows);
    this.root.append(
      reportIntro(
        "Beobachtete Kompositionen",
        "Nur tatsächlich erzeugte kanonische Compositions erscheinen hier. Es wird kein kartesisches Produkt möglicher Prompts berechnet.",
      ),
    );
    if (!rows.length) {
      this.root.append(emptyMessage("Keine Kombinationen für diesen Filter."));
      return;
    }
    const grid = document.createElement("div");
    grid.className = "analytics-composition-grid";
    for (const row of rows) grid.append(compositionCard(row));
    this.root.append(grid);
  }
}

/** @param {string} title @param {string} description */
function reportIntro(title, description) {
  const header = document.createElement("header");
  header.className = "analytics-report-intro";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.textContent = description;
  header.append(heading, copy);
  return header;
}

/** @param {Array<[string, unknown]>} metrics */
function metricStrip(metrics) {
  const strip = document.createElement("dl");
  strip.className = "analytics-metric-strip";
  for (const [label, value] of metrics) {
    const card = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = textValue(value);
    card.append(term, detail);
    strip.append(card);
  }
  return strip;
}

/** @param {Record<string, any>} payload @param {unknown} exampleValue */
function calculationExample(payload, exampleValue) {
  const example = recordValue(exampleValue);
  const section = document.createElement("section");
  section.className = "analytics-calculation";
  const title = document.createElement("h2");
  title.textContent = "So wird die Evidenz gelesen";
  const rule = document.createElement("p");
  rule.textContent = `Ratings ab ${textValue(payload.t)} zählen als Erfolg. Deletes fließen mit Gewicht ${textValue(payload.dw)} als Fehlschlag ein.`;
  const formula = document.createElement("code");
  formula.textContent =
    "erwarteter Erfolg = (Erfolg + 1) / (Erfolg + Fehlschlag + 2)";
  section.append(title, rule, formula);
  if (Object.keys(example).length) {
    const worked = document.createElement("p");
    worked.className = "analytics-worked-example";
    worked.textContent = `Beispiel: ${textValue(example.n)} Beobachtungen · Ø ${decimalValue(example.avg_rating)} / 10 · erwarteter Erfolg ${percentValue(example.exp_success_rate)} · konservative Untergrenze ${percentValue(example.stability_lb05)}.`;
    section.append(worked);
  }
  return section;
}

/** @param {string} title @param {unknown[]} items @param {string} tone */
function recommendationGroup(title, items, tone) {
  const section = document.createElement("section");
  section.className = "analytics-recommendations";
  section.dataset.tone = tone;
  const heading = document.createElement("h2");
  heading.textContent = title;
  const list = document.createElement("div");
  list.className = "analytics-recommendation-list";
  if (!items.length) list.append(emptyMessage("Keine Einträge."));
  for (const item of items) list.append(recommendationCard(item));
  section.append(heading, list);
  return section;
}

/** @param {unknown} value */
function recommendationCard(value) {
  const item = recordValue(value);
  const card = document.createElement("article");
  const label = document.createElement("strong");
  label.textContent = textValue(
    item.label || item.checkpoint || "Konfiguration",
  );
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(item.n)} Belege · Ø ${decimalValue(item.avg_rating ?? item.average_rating)} / 10`;
  const confidence = document.createElement("span");
  confidence.textContent = `Erwartet ${percentValue(item.exp_success_rate)} · Untergrenze ${percentValue(item.stability_lb05)}`;
  card.append(label, evidence, confidence);
  return card;
}

/** @param {Record<string, any>} approximate */
function approximationGroup(approximate) {
  const section = document.createElement("section");
  section.className = "analytics-approximation";
  const heading = document.createElement("h2");
  heading.textContent = "Rechnerische Kandidaten";
  const note = document.createElement("p");
  note.textContent = textValue(
    approximate.notes ||
      "Additive Schätzung aus beobachteten Parametern; noch keine getestete Kombination.",
  );
  section.append(heading, note);
  const rows = arrayValue(approximate.rows).slice(0, 8);
  if (!rows.length) {
    section.append(emptyMessage("Keine rechnerischen Kandidaten."));
    return section;
  }
  const grid = document.createElement("div");
  grid.className = "analytics-approx-grid";
  for (const row of rows) {
    const card = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = `${textValue(row.sampler)} · ${textValue(row.scheduler)}`;
    const settings = document.createElement("span");
    settings.textContent = `${textValue(row.steps)} Steps · CFG ${textValue(row.cfg)}`;
    const score = document.createElement("span");
    score.textContent = `${percentValue(row.pred_success)} prognostiziert · Support ${textValue(row.support_min)}`;
    card.append(title, settings, score);
    grid.append(card);
  }
  section.append(grid);
  return section;
}

/** @param {Record<string, any>} row */
function scopeCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-scope-card";
  card.dataset.kind = String(row.kind || "modifier");
  const header = document.createElement("header");
  const title = document.createElement("h3");
  title.textContent = textValue(row.name);
  header.append(title);
  if (row.archived) {
    const archived = document.createElement("span");
    archived.className = "analytics-archived";
    archived.textContent = "Archiviert";
    header.append(archived);
  }
  card.append(
    imageExamples(row.best_images, `Scope ${textValue(row.name)}`),
    header,
    evidenceLine(row),
  );
  return card;
}

/** @param {Record<string, any>} row */
function compositionCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-composition-card";
  card.append(imageExamples(row.best_images, "Komposition"));
  const scopes = document.createElement("div");
  scopes.className = "analytics-composition-scopes";
  for (const name of arrayValue(row.component_names)) {
    const chip = document.createElement("span");
    chip.textContent = textValue(name);
    scopes.append(chip);
  }
  if (!scopes.children.length) {
    const fallback = document.createElement("span");
    fallback.textContent = textValue(row.composition_uid);
    scopes.append(fallback);
  }
  card.append(scopes, evidenceLine(row));
  return card;
}

/** @param {unknown[]} values */
function bestCaseSection(values) {
  const section = document.createElement("section");
  section.className = "analytics-best-cases";
  section.append(
    reportIntro(
      "Best Case · berechnet",
      "Pro Checkpoint wird je Parameter der stabilste beobachtete Wert gewählt. Das ist eine nachvollziehbare Empfehlung, aber noch kein Beleg für die gemeinsame Kombination.",
    ),
  );
  if (!values.length) {
    section.append(emptyMessage("Keine berechneten Vorschläge."));
    return section;
  }
  const grid = document.createElement("div");
  grid.className = "analytics-best-grid";
  for (const value of values.slice(0, 5)) {
    const item = recordValue(value);
    const card = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = textValue(item.checkpoint);
    const picks = recordValue(item.picks);
    const settings = document.createElement("span");
    settings.textContent = [
      pickLabel(picks.sampler, "Sampler"),
      pickLabel(picks.scheduler, "Scheduler"),
      pickLabel(picks.steps, "Steps"),
      pickLabel(picks.cfg, "CFG"),
    ]
      .filter(Boolean)
      .join(" · ");
    const score = document.createElement("span");
    score.textContent = `Empfehlung ${percentValue(item.score)} · Checkpoint-Untergrenze ${percentValue(recordValue(item.checkpoint_stats).stability_lb05)}`;
    card.append(title, settings, score);
    grid.append(card);
  }
  section.append(grid);
  return section;
}

/** @param {Record<string, any>} row */
function parameterCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-parameter-card";
  const content = document.createElement("div");
  const value = document.createElement("strong");
  value.textContent = textValue(row.value);
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(row.n ?? row.sample_count)} Belege · Ø ${decimalValue(row.avg_rating ?? row.mean_score)} / 10`;
  const confidence = document.createElement("span");
  confidence.textContent = `Erwartet ${percentValue(row.exp_success_rate)} · Untergrenze ${percentValue(row.stability_lb05 ?? row.lb05)}`;
  content.append(value, evidence, confidence);
  card.append(content, imageExamples(row.best_images, String(row.value)));
  return card;
}

/** @param {Record<string, any>} row */
function evidenceLine(row) {
  const evidence = document.createElement("p");
  evidence.className = "analytics-evidence";
  const imageCount = Number(row.image_count);
  const ratingCount = Number(row.rating_count);
  const imageLabel = imageCount === 1 ? "Bild" : "Bilder";
  const ratingLabel = ratingCount === 1 ? "Bewertung" : "Bewertungen";
  evidence.textContent = `${textValue(row.image_count)} ${imageLabel} · ${textValue(row.rating_count)} ${ratingLabel} · Ø ${decimalValue(row.average_rating)} / 10`;
  return evidence;
}

/** @param {unknown} values @param {string} label */
function imageExamples(values, label) {
  const strip = document.createElement("div");
  strip.className = "analytics-image-strip";
  for (const value of arrayValue(values)) {
    const item = recordValue(value);
    if (!item.url) continue;
    const image = document.createElement("img");
    image.src = String(item.url);
    image.alt = `${label} · Ø ${decimalValue(item.avg_rating)} / 10`;
    image.loading = "lazy";
    strip.append(image);
  }
  if (!strip.children.length) {
    const empty = document.createElement("span");
    empty.textContent = "Kein Bildbeispiel";
    strip.append(empty);
  }
  strip.dataset.count = String(strip.children.length);
  return strip;
}

/** @param {unknown} value @param {string} label */
function pickLabel(value, label) {
  const pick = recordValue(value);
  return Object.keys(pick).length ? `${label} ${textValue(pick.value)}` : "";
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

/** @param {unknown} value @returns {Record<string, any>} */
function recordValue(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
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
function percentValue(value) {
  const number = Number(value);
  return Number.isFinite(number)
    ? `${numberFormatter.format(number * 100)} %`
    : "—";
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
