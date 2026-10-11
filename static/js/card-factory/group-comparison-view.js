/** Render four complete Card Candidates from server-authoritative artifacts. */
export class CardCandidateGroupComparisonView {
  /** @param {HTMLElement} root @param {{onAccept: (candidateId: string) => void}} actions */
  constructor(root, actions) {
    this.root = root;
    this.onAccept = actions.onAccept;
    this.status = requiredElement(root, "[data-comparison-status]");
    this.title = requiredElement(root, "[data-comparison-title]");
    this.summary = requiredElement(root, "[data-comparison-summary]");
    this.sourceImage = requiredImage(root, "[data-comparison-source]");
    this.facts = requiredElement(root, "[data-comparison-facts]");
    this.semantic = requiredElement(root, "[data-comparison-semantic]");
    this.imprint = requiredElement(root, "[data-comparison-imprint]");
    this.candidates = requiredElement(root, "[data-comparison-candidates]");
    this.rejectButton = requiredButton(root, "[data-reject-group]");
    this.retryButton = requiredButton(root, "[data-retry-group]");
  }

  /** @param {Record<string, any>} group */
  render(group) {
    this.title.textContent =
      group.kind === "development"
        ? "Kartenentwicklung vergleichen"
        : "Vier neue Karten vergleichen";
    this.summary.textContent = statusText(String(group.status));
    this.status.textContent = `Gruppe · Revision ${Number(group.revision || 0)}`;
    this.sourceImage.src = String(group.reference?.image_url || "");
    this.sourceImage.alt = "Aktive Referenz der Candidate-Gruppe";
    this.facts.replaceChildren(
      ...factRows([
        ["Typ", group.kind === "development" ? "Entwicklung" : "Erstellung"],
        ["Status", statusText(String(group.status))],
        ["Gruppe", String(group.group_id || "–")],
      ]),
    );
    this.semantic.replaceChildren(...semanticTags(group.semantic_profile));
    this.imprint.replaceChildren(...imprintRows(group.imprint));
    const candidates = Array.isArray(group.candidates) ? group.candidates : [];
    this.candidates.replaceChildren(
      ...candidates.map((candidate) => this.#candidate(candidate)),
    );
    this.rejectButton.hidden = !group.actions?.can_reject;
    this.retryButton.hidden = !group.actions?.can_retry;
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    this.rejectButton.disabled = busy;
    this.retryButton.disabled = busy;
    for (const button of this.candidates.querySelectorAll("button")) {
      button.disabled = busy || button.dataset.allowed !== "true";
    }
  }

  /** @param {string} text */
  showError(text) {
    this.status.textContent = text;
  }

  dispose() {
    this.candidates.replaceChildren();
  }

  /** @param {Record<string, any>} candidate */
  #candidate(candidate) {
    const article = document.createElement("article");
    article.className = "complete-card-candidate";
    article.dataset.status = String(candidate.status || "unknown");
    const artifacts = candidate.artifacts;
    const card = artifacts?.card;
    const presentation = artifacts?.presentation?.presentation;
    const image = candidate.image_url
      ? document.createElement("img")
      : placeholder("Bild wird erzeugt");
    if (image instanceof HTMLImageElement) {
      image.src = String(candidate.image_url);
      image.alt = `Kartenkandidat ${Number(candidate.slot_index) + 1}`;
    }
    const header = document.createElement("header");
    const eyebrow = document.createElement("span");
    eyebrow.className = "complete-card-eyebrow";
    eyebrow.textContent = card
      ? `${String(card.rarity_key).toUpperCase()} · L${Number(card.level)}`
      : `SLOT ${Number(candidate.slot_index) + 1}`;
    const title = document.createElement("h2");
    title.className = "complete-card-title";
    title.textContent = String(
      presentation?.card_title || statusText(String(candidate.status)),
    );
    header.append(eyebrow, title);
    const body = document.createElement("div");
    body.className = "complete-card-body";
    if (card) body.append(stats(card.stats), ...traits(card, presentation));
    if (presentation?.short_description) {
      body.append(paragraph(presentation.short_description));
    }
    const diagnostics = document.createElement("details");
    const diagnosticsTitle = document.createElement("summary");
    diagnosticsTitle.textContent = "Recipe & Diagnostics";
    diagnostics.append(
      diagnosticsTitle,
      ...recipeDetails(artifacts?.visual_recipe, candidate.failure_category),
    );
    const footer = document.createElement("footer");
    const state = document.createElement("span");
    state.className = "card-candidate-status";
    state.textContent = statusText(String(candidate.status));
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "primary-button";
    accept.textContent = candidate.can_accept
      ? "Diese Karte wählen"
      : "Nicht wählbar";
    accept.dataset.allowed = candidate.can_accept ? "true" : "false";
    accept.disabled = !candidate.can_accept;
    accept.addEventListener("click", () =>
      this.onAccept(String(candidate.candidate_id)),
    );
    footer.append(state, accept);
    article.append(header, image, body, diagnostics, footer);
    return article;
  }
}

/** @param {Record<string, any>} values */
function stats(values) {
  const row = document.createElement("div");
  row.className = "prototype-card-stats";
  for (const [label, value] of [
    ["ATK", values.attack],
    ["DEF", values.defense],
  ]) {
    const item = document.createElement("span");
    item.textContent = `${label} `;
    const strong = document.createElement("strong");
    strong.textContent = String(value ?? "–");
    item.append(strong);
    row.append(item);
  }
  return row;
}

/** @param {Record<string, any>} card @param {Record<string, any>|undefined} presentation */
function traits(card, presentation) {
  const names = Array.isArray(presentation?.trait_display_names)
    ? presentation.trait_display_names
    : [];
  return (Array.isArray(card.traits) ? card.traits : []).map((trait, index) => {
    const section = document.createElement("section");
    section.className = "card-trait";
    const heading = document.createElement("h3");
    heading.textContent = String(
      names[index] || trait.mechanic?.key || "Trait",
    );
    const rule = paragraph(String(trait.canonical_rule_text || ""));
    section.append(heading, rule);
    return section;
  });
}

/** @param {Record<string, any>|undefined} recipe @param {unknown} failure */
function recipeDetails(recipe, failure) {
  const rows = [];
  if (failure) rows.push(paragraph(`Fehler: ${String(failure)}`));
  for (const diagnostic of recipe?.diagnostics || []) {
    rows.push(paragraph(`${diagnostic.code}: ${diagnostic.message}`));
  }
  if (!rows.length) rows.push(paragraph("Keine Diagnostics."));
  return rows;
}

/** @param {Record<string, any>|null|undefined} profile */
function semanticTags(profile) {
  if (!profile) return [paragraph("Analyse läuft …")];
  const values = [
    profile.summary,
    ...(profile.subjects || []),
    ...(profile.actions || []),
    ...(profile.mood || []),
    ...(profile.environment || []),
  ].filter(Boolean);
  return values.map((value) => tag(String(value)));
}

/** @param {Record<string, any>|null|undefined} imprint */
function imprintRows(imprint) {
  if (!imprint) return [paragraph("Mapping läuft …")];
  return factRows([
    ["World", imprint.world_style],
    ["Class", imprint.card_class],
    ["Role", imprint.combat_role],
    ["Lineage", imprint.trait_lineage],
  ]);
}

/** @param {Array<[string, unknown]>} rows */
function factRows(rows) {
  return rows.flatMap(([label, value]) => {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = String(value ?? "–");
    return [term, detail];
  });
}

/** @param {string} text */
function tag(text) {
  const span = document.createElement("span");
  span.className = "card-tag";
  span.textContent = text;
  return span;
}

/** @param {string} text */
function paragraph(text) {
  const node = document.createElement("p");
  node.textContent = text;
  return node;
}

/** @param {string} text */
function placeholder(text) {
  const node = document.createElement("div");
  node.className = "card-candidate-placeholder";
  node.textContent = text;
  return node;
}

/** @param {string} status */
function statusText(status) {
  return (
    {
      queued: "Eingereiht",
      composing: "Karte wird aufgebaut",
      submitted: "Bild eingereicht",
      generating: "Bilder werden erzeugt",
      completed: "Bereit",
      ready: "Vergleichsbereit",
      partial_failure: "Teilweise bereit",
      failed: "Fehlgeschlagen",
      accepted: "Angenommen",
      rejected: "Verworfen",
    }[status] || status
  );
}

/** @param {ParentNode} root @param {string} selector */
function requiredElement(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLElement)) throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {ParentNode} root @param {string} selector */
function requiredButton(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLButtonElement))
    throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {ParentNode} root @param {string} selector */
function requiredImage(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLImageElement))
    throw new Error(`Missing ${selector}`);
  return element;
}
