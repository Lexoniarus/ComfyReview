const numberFormatter = new Intl.NumberFormat("de-DE", {
  maximumFractionDigits: 2,
});

const parameterLabels = new Map([
  ["checkpoint", "Checkpoint"],
  ["steps", "Steps"],
  ["cfg", "CFG"],
  ["sampler", "Sampler"],
  ["scheduler", "Scheduler"],
]);

const scopeKindLabels = new Map([
  ["character", "Charakter"],
  ["scene", "Szene"],
  ["outfit", "Outfit"],
  ["pose", "Pose"],
  ["expression", "Ausdruck"],
  ["lighting", "Licht"],
  ["modifier", "Modifier"],
]);

/** Render server-computed analytics without reproducing statistics in-browser. */
export class AnalyticsView {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
  }

  /** @param {string} section @param {Record<string, any>} payload */
  render(section, payload) {
    this.clear();
    if (section === "overview") renderOverview(this.root, payload);
    else if (section === "scopes") renderScopes(this.root, payload);
    else if (section === "parameters") renderParameters(this.root, payload);
    else renderCombinations(this.root, payload);
  }

  /**
   * Add the requested setup evidence to its prompt-composition card.
   * @param {string} compositionUid
   * @param {Record<string, any>} payload
   */
  renderCompositionSetups(compositionUid, payload) {
    const card = this.root.querySelector(
      `[data-composition-uid="${CSS.escape(compositionUid)}"]`,
    );
    if (!(card instanceof HTMLElement)) return;
    const existing = card.querySelector("[data-composition-setups]");
    const details = document.createElement("section");
    details.dataset.compositionSetups = "";
    details.className = "analytics-composition-setups";
    const title = document.createElement("h3");
    title.textContent = "Beobachtete Render-Setups";
    const rows = arrayValue(payload.rows);
    details.append(title);
    if (!rows.length) details.append(emptyMessage("Keine technischen Setups."));
    for (const row of rows) details.append(renderSetupCard(row));
    if (existing) existing.replaceWith(details);
    else card.append(details);
  }

  /** Clear rendered report content. */
  clear() {
    this.root.replaceChildren();
  }
}

/** @param {HTMLElement} root @param {Record<string, any>} payload */
function renderOverview(root, payload) {
  const stable = arrayValue(payload.stable);
  const avoid = arrayValue(payload.avoid);
  const approximate = recordValue(payload.approx);
  root.append(
    reportIntro(
      "Entscheidungshilfe",
      "Beobachtete Evidenz und rechnerische Kandidaten bleiben klar getrennt.",
    ),
    metricStrip([
      ["Stabil", stable.length],
      ["Vermeiden", avoid.length],
      ["Beobachtungen", recordValue(approximate.base).n],
    ]),
  );
  const grid = document.createElement("div");
  grid.className = "analytics-overview-grid";
  grid.append(
    recommendationGroup("Stabile Empfehlungen", stable),
    recommendationGroup("Vermeiden", avoid),
  );
  root.append(grid, approximationGroup(approximate));
}

/** @param {HTMLElement} root @param {Record<string, any>} payload */
function renderScopes(root, payload) {
  const rows = arrayValue(payload.rows);
  root.append(
    reportIntro(
      "Scope-Evidenz",
      "Kanonische Prompt-Komponenten mit realen Bildbeispielen.",
    ),
  );
  if (!rows.length) {
    root.append(emptyMessage("Keine Scopes für diesen Filter."));
    return;
  }
  for (const [kind, label] of scopeKindLabels) {
    const matches = rows.filter((row) => String(row.kind) === kind);
    if (!matches.length) continue;
    const section = document.createElement("section");
    section.className = "analytics-scope-section";
    const title = document.createElement("h2");
    title.textContent = label;
    const grid = document.createElement("div");
    grid.className = "analytics-scope-grid";
    for (const row of matches) grid.append(scopeCard(row));
    section.append(title, grid);
    root.append(section);
  }
}

/** @param {HTMLElement} root @param {Record<string, any>} payload */
function renderParameters(root, payload) {
  const view = String(payload.view || "summary");
  root.append(
    reportIntro(
      "Renderparameter",
      "Rechnerische Empfehlungen, beobachtete Setups und Einzelparameter werden getrennt ausgewertet.",
    ),
    parameterNavigation(view, String(payload.parameter || "")),
  );
  if (view === "values") {
    const rows = arrayValue(payload.rows);
    const grid = document.createElement("div");
    grid.className = "analytics-parameter-grid";
    for (const row of rows) grid.append(parameterCard(row));
    root.append(
      sectionTitle(parameterLabels.get(String(payload.parameter)) || "Werte"),
      rows.length ? grid : emptyMessage("Keine Werte für diesen Parameter."),
    );
    return;
  }
  const recommendations = arrayValue(payload.recommendations);
  const observed = arrayValue(payload.observed_setups);
  root.append(
    sectionTitle("Rechnerische Empfehlung · nicht gemeinsam getestet"),
    recommendationGrid(recommendations),
    sectionTitle("Beobachtete vollständige Setups"),
    setupGrid(observed),
  );
}

/** @param {HTMLElement} root @param {Record<string, any>} payload */
function renderCombinations(root, payload) {
  const view = String(payload.view || "prompt");
  const rows = arrayValue(payload.rows);
  root.append(
    reportIntro(
      view === "render" ? "Beobachtete Render-Setups" : "Prompt-Kombinationen",
      "Nur tatsächlich verwendete kanonische Fakten werden gezeigt; mögliche Kreuzprodukte entstehen nicht.",
    ),
    combinationNavigation(view),
  );
  if (!rows.length) {
    root.append(emptyMessage("Keine Kombinationen für diesen Filter."));
    return;
  }
  if (view === "render") root.append(setupGrid(rows));
  else {
    const grid = document.createElement("div");
    grid.className = "analytics-composition-grid";
    for (const row of rows) grid.append(compositionCard(row));
    root.append(grid);
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

/** @param {string} selectedView */
function combinationNavigation(selectedView) {
  const navigation = document.createElement("nav");
  navigation.className = "analytics-subtabs";
  navigation.setAttribute("aria-label", "Kombinationsansicht");
  navigation.append(
    viewButton("Prompt-Kombinationen", "prompt", "", selectedView, ""),
    viewButton("Render-Setups", "render", "", selectedView, ""),
  );
  return navigation;
}

/** @param {string} label @param {string} view @param {string} parameter @param {string} selectedView @param {string} selectedParameter */
function viewButton(label, view, parameter, selectedView, selectedParameter) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.dataset.analyticsView = view;
  if (parameter) button.dataset.analyticsParameter = parameter;
  const selected = view === selectedView && parameter === selectedParameter;
  button.setAttribute("aria-pressed", String(selected));
  return button;
}

/** @param {unknown[]} values */
function recommendationGrid(values) {
  if (!values.length) return emptyMessage("Keine rechnerischen Empfehlungen.");
  const grid = document.createElement("div");
  grid.className = "analytics-best-grid";
  for (const value of values) {
    const item = recordValue(value);
    const card = document.createElement("article");
    const title = document.createElement("strong");
    title.textContent = textValue(item.checkpoint);
    const settings = document.createElement("span");
    settings.textContent = settingLine(item);
    const score = document.createElement("span");
    score.textContent = `Prognose ${percentValue(item.score)} · Checkpoint-Untergrenze ${percentValue(item.checkpoint_lower_bound)}`;
    card.append(title, settings, score);
    grid.append(card);
  }
  return grid;
}

/** @param {unknown[]} rows */
function setupGrid(rows) {
  if (!rows.length) return emptyMessage("Keine beobachteten Setups.");
  const grid = document.createElement("div");
  grid.className = "analytics-tested-list";
  for (const row of rows) grid.append(renderSetupCard(row));
  return grid;
}

/** @param {unknown} value */
function renderSetupCard(value) {
  const item = recordValue(value);
  const card = document.createElement("article");
  card.className = "analytics-render-setup";
  const title = document.createElement("strong");
  title.textContent = textValue(item.checkpoint);
  card.append(title);
  for (const stage of arrayValue(item.stages)) {
    const line = document.createElement("span");
    line.textContent = stageLine(recordValue(stage));
    card.append(line);
  }
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(item.image_count)} Bilder · ${textValue(item.rating_count)} Bewertungen · Ø ${decimalValue(item.average_rating)} / 10 · Untergrenze ${percentValue(item.lower_bound)}`;
  card.append(evidence, imageExamples(item.best_images, "Render-Setup"));
  return card;
}

/** @param {Record<string, any>} stage */
function stageLine(stage) {
  return `${textValue(stage.role)} · ${textValue(stage.sampler)} / ${textValue(stage.scheduler)} · ${textValue(stage.steps)} Steps · CFG ${textValue(stage.cfg)} · Denoise ${textValue(stage.denoise)}`;
}

/** @param {Record<string, any>} row */
function parameterCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-parameter-card";
  const content = document.createElement("div");
  const value = document.createElement("strong");
  value.textContent = textValue(row.value);
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(row.sample_count)} Belege · Ø ${decimalValue(row.average_rating)} / 10`;
  const confidence = document.createElement("span");
  confidence.textContent = `Erwartet ${percentValue(row.expected_success_rate)} · Untergrenze ${percentValue(row.lower_bound)}`;
  content.append(value, evidence, confidence);
  card.append(content, imageExamples(row.best_images, String(row.value)));
  return card;
}

/** @param {Record<string, any>} row */
function scopeCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-scope-card";
  card.dataset.kind = String(row.kind || "modifier");
  const title = document.createElement("h3");
  title.textContent = textValue(row.name);
  card.append(imageExamples(row.best_images, String(row.name)), title);
  if (row.archived) {
    const archived = document.createElement("span");
    archived.className = "analytics-archived";
    archived.textContent = "Archiviert";
    card.append(archived);
  }
  card.append(evidenceLine(row));
  return card;
}

/** @param {Record<string, any>} row */
function compositionCard(row) {
  const card = document.createElement("article");
  card.className = "analytics-composition-card";
  card.dataset.compositionUid = String(row.composition_uid || "");
  card.append(imageExamples(row.best_images, "Prompt-Kombination"));
  const scopes = document.createElement("div");
  scopes.className = "analytics-composition-scopes";
  const names = arrayValue(row.component_names);
  for (const name of names) {
    const chip = document.createElement("span");
    chip.textContent = textValue(name);
    scopes.append(chip);
  }
  if (!names.length) scopes.append(textValue(row.composition_uid));
  const details = document.createElement("button");
  details.type = "button";
  details.dataset.compositionDetails = String(row.composition_uid || "");
  details.textContent = "Technische Setups anzeigen";
  card.append(scopes, evidenceLine(row), details);
  return card;
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

/** @param {string} text */
function sectionTitle(text) {
  const title = document.createElement("h2");
  title.textContent = text;
  return title;
}

/** @param {Array<[string, unknown]>} metrics */
function metricStrip(metrics) {
  const strip = document.createElement("dl");
  strip.className = "analytics-metric-strip";
  for (const [label, value] of metrics) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = textValue(value);
    item.append(term, detail);
    strip.append(item);
  }
  return strip;
}

/** @param {string} title @param {unknown[]} rows */
function recommendationGroup(title, rows) {
  const section = document.createElement("section");
  section.className = "analytics-recommendations";
  section.append(sectionTitle(title));
  if (!rows.length) section.append(emptyMessage("Keine Einträge."));
  for (const value of rows) {
    const item = recordValue(value);
    const card = document.createElement("article");
    card.textContent = `${textValue(item.label || item.checkpoint)} · ${textValue(item.n)} Belege · Ø ${decimalValue(item.avg_rating)} / 10`;
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
  if (!rows.length)
    section.append(emptyMessage("Keine rechnerischen Kandidaten."));
  for (const value of rows) {
    const item = recordValue(value);
    const card = document.createElement("article");
    card.textContent = `${settingLine(item)} · ${percentValue(item.pred_success)} prognostiziert`;
    section.append(card);
  }
  return section;
}

/** @param {Record<string, any>} item */
function settingLine(item) {
  return `${textValue(item.sampler)} · ${textValue(item.scheduler)} · ${textValue(item.steps)} Steps · CFG ${textValue(item.cfg)}`;
}

/** @param {Record<string, any>} row */
function evidenceLine(row) {
  const line = document.createElement("p");
  line.className = "analytics-evidence";
  line.textContent = `${textValue(row.image_count)} Bilder · ${textValue(row.rating_count)} Bewertungen · Ø ${decimalValue(row.average_rating)} / 10`;
  return line;
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
