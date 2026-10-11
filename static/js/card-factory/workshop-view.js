/** Render server-projected Card facts without reproducing game rules. */
export class CardWorkshopView {
  /** @param {HTMLElement} root @param {{onAccept: (candidateId: string) => void}} callbacks */
  constructor(root, callbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.abortController = new AbortController();
    this.status = requiredElement(root, "[data-workshop-status]");
    this.generateButton = requiredButton(root, "[data-generate-candidates]");
    this.developButton = requiredButton(root, "[data-develop-card]");
    this.candidates = requiredElement(root, "[data-card-candidates]");
  }

  /** @param {Record<string, any>} session */
  render(session) {
    const presentation = objectValue(session.presentation);
    const card = objectValue(session.card_spec);
    const stats = objectValue(card.stats);
    const imprint = objectValue(session.imprint);
    const semantic = objectValue(session.semantic_profile);
    const recipe = objectValue(session.visual_recipe);
    const activeReference = objectValue(session.active_reference);
    const actions = objectValue(session.actions);
    const traits = Array.isArray(card.traits) ? card.traits : [];
    const displayNames = Array.isArray(presentation.trait_display_names)
      ? presentation.trait_display_names
      : [];

    setText(
      this.root,
      "[data-card-title]",
      presentation.card_title || "Card Workshop",
    );
    setText(
      this.root,
      "[data-preview-title]",
      presentation.card_title || "Unbenannte Karte",
    );
    setText(
      this.root,
      "[data-card-summary]",
      presentation.short_description ||
        semantic.summary ||
        "Mechanisch gültige Karte ohne kosmetische Presentation.",
    );
    setText(this.root, "[data-card-flavor]", presentation.flavor_text || "");
    setText(
      this.root,
      "[data-card-rarity]",
      `${String(card.rarity_key || "card").toUpperCase()} · L${String(card.level || "–")}`,
    );
    setText(
      this.root,
      "#card-heading",
      `${title(String(card.rarity_key || "Card"))} L${String(card.level || "–")}`,
    );
    setText(this.root, "[data-card-attack]", String(stats.attack ?? "–"));
    setText(this.root, "[data-card-defense]", String(stats.defense ?? "–"));
    setImage(this.root, "[data-active-image]", activeReference.image_url);
    setImage(this.root, "[data-card-image]", activeReference.image_url);

    renderFacts(requiredElement(this.root, "[data-source-facts]"), [
      ["Bild", activeReference.image_uid],
      ["Art", activeReference.kind],
      ["Visual Tier", activeReference.visual_tier],
      ["Revision", session.revision],
    ]);
    renderFacts(requiredElement(this.root, "[data-card-imprint]"), [
      ["World Style", imprint.world_style],
      ["Class", imprint.card_class],
      ["Role", imprint.combat_role],
      ["Lineage", imprint.trait_lineage],
      ["Stat Profile", stats.stat_profile_key],
    ]);
    renderSemantic(
      requiredElement(this.root, "[data-semantic-profile]"),
      semantic,
    );
    renderTraits(
      requiredElement(this.root, "[data-card-traits]"),
      traits,
      displayNames,
    );
    renderAtoms(
      requiredElement(this.root, "[data-positive-atoms]"),
      recipe.positive_atoms,
    );
    renderAtoms(
      requiredElement(this.root, "[data-negative-atoms]"),
      recipe.negative_atoms,
    );
    renderDiagnostics(
      requiredElement(this.root, "[data-recipe-diagnostics]"),
      recipe.diagnostics,
    );
    this.#renderCandidates(
      Array.isArray(session.candidates) ? session.candidates : [],
    );

    this.generateButton.disabled = actions.can_generate !== true;
    this.developButton.disabled = actions.can_develop !== true;
    this.status.textContent = statusText(session);
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    if (busy) {
      this.generateButton.disabled = true;
      this.developButton.disabled = true;
      this.status.textContent = "Aktion läuft …";
    }
  }

  /** @param {string} text */
  showError(text) {
    this.status.textContent = text;
  }

  /** Dispose candidate button listeners. */
  dispose() {
    this.abortController.abort();
  }

  /** @param {Array<Record<string, any>>} candidates */
  #renderCandidates(candidates) {
    if (!candidates.length) {
      this.candidates.replaceChildren(
        message(
          "card-empty-state",
          "Noch keine Kandidaten. Die aktuelle Recipe kann vier neue Varianten erzeugen.",
        ),
      );
      return;
    }
    this.candidates.replaceChildren(
      ...candidates.map((candidate) => this.#candidate(candidate)),
    );
  }

  /** @param {Record<string, any>} candidate */
  #candidate(candidate) {
    const article = document.createElement("article");
    article.className = "card-candidate";
    article.dataset.status = String(candidate.status || "pending");
    if (candidate.image_url) {
      const image = document.createElement("img");
      image.src = String(candidate.image_url);
      image.alt = `Evolution-Kandidat ${Number(candidate.slot_index) + 1}`;
      article.append(image);
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "card-candidate-placeholder";
      placeholder.textContent = `Slot ${Number(candidate.slot_index) + 1}`;
      article.append(placeholder);
    }
    const footer = document.createElement("footer");
    const state = document.createElement("span");
    state.className = "card-candidate-status";
    state.textContent = String(candidate.status || "pending");
    footer.append(state);
    if (candidate.failure_category) {
      footer.append(message("muted", String(candidate.failure_category)));
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.textContent =
      candidate.status === "accepted" ? "Angenommen" : "Kandidat annehmen";
    button.disabled = candidate.can_accept !== true;
    button.addEventListener(
      "click",
      () => this.callbacks.onAccept(String(candidate.candidate_id || "")),
      { signal: this.abortController.signal },
    );
    footer.append(button);
    article.append(footer);
    return article;
  }
}

/** @param {ParentNode} root @param {string} selector @param {unknown} value */
function setText(root, selector, value) {
  requiredElement(root, selector).textContent = String(value || "");
}

/** @param {ParentNode} root @param {string} selector @param {unknown} source */
function setImage(root, selector, source) {
  const image = root.querySelector(selector);
  if (!(image instanceof HTMLImageElement))
    throw new Error(`Missing ${selector}`);
  image.src = String(source || "");
}

/** @param {HTMLElement} root @param {Array<[string, unknown]>} facts */
function renderFacts(root, facts) {
  const nodes = [];
  for (const [name, value] of facts) {
    const term = document.createElement("dt");
    term.textContent = name;
    const description = document.createElement("dd");
    description.textContent = String(value ?? "–");
    nodes.push(term, description);
  }
  root.replaceChildren(...nodes);
}

/** @param {HTMLElement} root @param {Record<string, any>} semantic */
function renderSemantic(root, semantic) {
  const groups = ["subjects", "actions", "mood", "environment", "objects"];
  const container = document.createElement("div");
  container.className = "card-tag-list";
  for (const group of groups) {
    const values = Array.isArray(semantic[group]) ? semantic[group] : [];
    for (const value of values)
      container.append(tag(`${group}: ${String(value)}`));
  }
  const signals = Array.isArray(semantic.signals) ? semantic.signals : [];
  for (const signal of signals) {
    container.append(
      tag(`${String(signal.concept_key)} · ${String(signal.strength_milli)}`),
    );
  }
  root.replaceChildren(container);
}

/** @param {HTMLElement} root @param {Array<Record<string, any>>} traits @param {unknown[]} displayNames */
function renderTraits(root, traits, displayNames) {
  root.replaceChildren(
    ...traits.map((trait, index) => {
      const article = document.createElement("article");
      article.className = "card-trait";
      const heading = document.createElement("h3");
      const mechanic = objectValue(trait.mechanic);
      heading.textContent = String(
        displayNames[index] || mechanic.key || `Trait ${index + 1}`,
      );
      const rule = document.createElement("p");
      rule.textContent = String(trait.canonical_rule_text || "");
      article.append(heading, rule);
      return article;
    }),
  );
}

/** @param {HTMLElement} root @param {unknown} rawAtoms */
function renderAtoms(root, rawAtoms) {
  const atoms = Array.isArray(rawAtoms) ? rawAtoms : [];
  root.replaceChildren(
    ...atoms.map((atom) => {
      const chip = tag(
        `${String(atom.canonical_text)} · ${(Number(atom.weight_milli || 0) / 1000).toFixed(2)}`,
      );
      chip.className = "prompt-chip";
      chip.dataset.required = String(atom.required === true);
      return chip;
    }),
  );
}

/** @param {HTMLElement} root @param {unknown} rawDiagnostics */
function renderDiagnostics(root, rawDiagnostics) {
  const diagnostics = Array.isArray(rawDiagnostics) ? rawDiagnostics : [];
  root.replaceChildren(
    ...(diagnostics.length
      ? diagnostics.map((item) =>
          message("muted", `${String(item.code)} · ${String(item.message)}`),
        )
      : [message("muted", "Keine Diagnostics")]),
  );
}

/** @param {Record<string, any>} session */
function statusText(session) {
  const candidates = Array.isArray(session.candidates)
    ? session.candidates
    : [];
  const active = candidates.filter((item) =>
    ["pending", "submitted"].includes(String(item.status)),
  ).length;
  if (active) return `${active} Kandidaten werden verarbeitet`;
  if (session.operation_state === "generating")
    return "Kandidaten bereit zur Auswahl";
  return `Session Revision ${String(session.revision || "–")}`;
}

/** @param {unknown} value @returns {Record<string, any>} */
function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

/** @param {string} text */
function tag(text) {
  const element = document.createElement("span");
  element.className = "card-tag";
  element.textContent = text;
  return element;
}

/** @param {string} className @param {string} text */
function message(className, text) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  paragraph.textContent = text;
  return paragraph;
}

/** @param {string} value */
function title(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
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
