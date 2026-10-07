/** @typedef {"character" | "scene" | "outfit" | "pose" | "expression" | "lighting" | "modifier"} ScopeKind */

/** @type {Record<ScopeKind, string>} */
const KIND_LABELS = {
  character: "Charakter",
  scene: "Szene",
  outfit: "Outfit",
  pose: "Pose",
  expression: "Ausdruck",
  lighting: "Licht",
  modifier: "Modifier",
};

/** Own scope controls and their DOM listeners. */
export class ScopeNavigator {
  /**
   * @param {HTMLElement} root
   * @param {{onToggle: (uid: string) => void, onClassification: (value: string) => void}} callbacks
   */
  constructor(root, callbacks) {
    this.root = root;
    this.callbacks = callbacks;
    this.events = new AbortController();
    /** @type {ScopeKind} */
    this.activeKind = "character";
    /** @type {Array<Record<string, unknown>>} */
    this.facets = [];
    /** @type {string[]} */
    this.selected = [];
    this.classification = "all";
    this.root.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
        const kindTab = target.closest("[data-scope-kind-tab]");
        if (kindTab instanceof HTMLElement && kindTab.dataset.scopeKindTab) {
          this.activeKind = /** @type {ScopeKind} */ (
            kindTab.dataset.scopeKindTab
          );
          this.#renderCurrent();
          return;
        }
        const button = target.closest("[data-scope-uid]");
        if (button instanceof HTMLElement && button.dataset.scopeUid) {
          this.callbacks.onToggle(button.dataset.scopeUid);
        }
      },
      { signal: this.events.signal },
    );
    this.root.addEventListener(
      "change",
      (event) => {
        const target = event.target;
        if (
          target instanceof HTMLSelectElement &&
          target.name === "classification"
        ) {
          this.callbacks.onClassification(target.value);
        }
      },
      { signal: this.events.signal },
    );
  }

  /** @param {Array<Record<string, unknown>>} facets @param {string[]} selected @param {string} classification */
  render(facets, selected, classification) {
    this.facets = facets;
    this.selected = selected;
    this.classification = classification;
    if (!facets.some((facet) => facet.kind === this.activeKind)) {
      this.activeKind = firstAvailableKind(facets);
    }
    this.#renderCurrent();
  }

  #renderCurrent() {
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "v2-panel-heading";
    const headingText = document.createElement("span");
    headingText.textContent = "Bereiche";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "icon-button scope-close";
    close.dataset.railAction = "scope";
    close.setAttribute("aria-label", "Bereiche schließen");
    close.textContent = "×";
    heading.append(headingText, close);
    this.root.append(
      heading,
      classificationControl(this.classification),
      kindTabs(this.facets, this.activeKind),
    );
    const matching = this.facets.filter(
      (facet) => facet.kind === this.activeKind,
    );
    if (matching.length === 0) return;
    const section = document.createElement("section");
    section.className = "scope-group";
    section.setAttribute("role", "tabpanel");
    section.setAttribute("aria-label", KIND_LABELS[this.activeKind]);
    for (const facet of matching) {
      section.append(scopeButton(facet, this.selected));
    }
    this.root.append(section);
  }

  /** Release every DOM listener owned by this component. */
  dispose() {
    this.events.abort();
  }
}

/** @param {Array<Record<string, unknown>>} facets @returns {ScopeKind} */
function firstAvailableKind(facets) {
  return /** @type {ScopeKind} */ (
    Object.keys(KIND_LABELS).find((kind) =>
      facets.some((facet) => facet.kind === kind),
    ) || "character"
  );
}

/** @param {Array<Record<string, unknown>>} facets @param {string} activeKind */
function kindTabs(facets, activeKind) {
  const navigation = document.createElement("div");
  navigation.className = "scope-kind-tabs";
  navigation.setAttribute("role", "tablist");
  navigation.setAttribute("aria-label", "Scope-Art");
  for (const [kind, label] of Object.entries(KIND_LABELS)) {
    if (!facets.some((facet) => facet.kind === kind)) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.scopeKindTab = kind;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(kind === activeKind));
    button.classList.toggle("is-active", kind === activeKind);
    button.textContent = label;
    navigation.append(button);
  }
  return navigation;
}

/** @param {string} value */
function classificationControl(value) {
  const label = document.createElement("label");
  label.className = "scope-classification";
  const text = document.createElement("span");
  text.textContent = "Klassifikation";
  const select = document.createElement("select");
  select.name = "classification";
  for (const [optionValue, optionLabel] of [
    ["all", "Alle Bilder"],
    ["classified", "Klassifiziert"],
    ["unclassified", "Unklassifiziert"],
  ]) {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionLabel;
    option.selected = optionValue === value;
    select.append(option);
  }
  label.append(text, select);
  return label;
}

/** @param {Record<string, unknown>} facet @param {string[]} selected */
function scopeButton(facet, selected) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "scope-option";
  const uid = String(facet.component_uid || "");
  button.dataset.scopeUid = uid;
  button.dataset.scopeKind = String(facet.kind || "");
  button.classList.toggle("is-selected", selected.includes(uid));
  button.setAttribute("aria-pressed", String(selected.includes(uid)));
  const name = document.createElement("span");
  name.textContent = String(facet.name || "Unbenannt");
  const count = document.createElement("span");
  count.className = "scope-count";
  count.textContent = String(facet.count ?? 0);
  if (facet.archived === true) {
    const archived = document.createElement("span");
    archived.className = "scope-archived";
    archived.textContent = "Archiv";
    name.append(" ", archived);
  }
  button.append(name, count);
  return button;
}
