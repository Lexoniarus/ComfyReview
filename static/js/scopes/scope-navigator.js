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
    this.root.addEventListener(
      "click",
      (event) => {
        const target = event.target;
        if (!(target instanceof Element)) return;
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
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "v2-panel-heading";
    heading.textContent = "Bereiche";
    this.root.append(heading, classificationControl(classification));
    for (const [kind, label] of Object.entries(KIND_LABELS)) {
      const matching = facets.filter((facet) => facet.kind === kind);
      if (matching.length === 0) continue;
      const section = document.createElement("section");
      section.className = "scope-group";
      const title = document.createElement("h2");
      title.textContent = label;
      section.append(title);
      for (const facet of matching) {
        section.append(scopeButton(facet, selected));
      }
      this.root.append(section);
    }
  }

  /** Release every DOM listener owned by this component. */
  dispose() {
    this.events.abort();
  }
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
