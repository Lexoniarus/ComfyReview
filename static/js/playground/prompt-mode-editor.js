const promptKinds = [
  ["character", "Charakter"],
  ["scene", "Szene"],
  ["outfit", "Outfit"],
  ["pose", "Pose"],
  ["expression", "Ausdruck"],
  ["lighting", "Licht"],
  ["modifier", "Modifier"],
];

/** Own fixed, random and disabled prompt-role controls. */
export class PromptModeEditor {
  /** @param {HTMLElement} root @param {HTMLInputElement} seedInput */
  constructor(root, seedInput) {
    this.root = root;
    this.seedInput = seedInput;
    this.abortController = new AbortController();
    /** @type {Map<string, {mode: HTMLSelectElement, component: HTMLSelectElement}>} */
    this.rows = new Map();
  }

  /** @param {Array<Record<string, any>>} components */
  render(components) {
    this.root.replaceChildren();
    this.rows.clear();
    const list = document.createElement("div");
    list.className = "prompt-mode-list";
    for (const [kind, label] of promptKinds) {
      const row = this.#row(kind, label, components);
      list.append(row.element);
      this.rows.set(kind, row.controls);
    }
    this.root.append(list);
  }

  /** Return the complete API selection intent. */
  value() {
    const selections = promptKinds.map(([kind]) => {
      const row = this.rows.get(kind);
      return {
        kind,
        mode: row?.mode.value || "random",
        component_uid: row?.mode.value === "fixed" ? row.component.value : null,
      };
    });
    const seed = Number.parseInt(this.seedInput.value, 10);
    return { selections, seed: Number.isFinite(seed) ? seed : null };
  }

  /** Release owned input listeners. */
  dispose() {
    this.abortController.abort();
    this.rows.clear();
  }

  /** @param {string} kind @param {string} label @param {Array<Record<string, any>>} components */
  #row(kind, label, components) {
    const element = document.createElement("div");
    element.className = "prompt-mode-row";
    element.dataset.kind = kind;
    const title = document.createElement("span");
    title.className = "prompt-kind-label";
    title.textContent = label;
    const mode = document.createElement("select");
    mode.setAttribute("aria-label", `${label}: Modus`);
    mode.append(option("fixed", "fixiert"), option("random", "zufällig"));
    if (kind !== "character") mode.append(option("off", "aus"));
    mode.value = kind === "character" ? "fixed" : "random";
    const component = document.createElement("select");
    component.setAttribute("aria-label", `${label}: Katalogeintrag`);
    const matching = components.filter((item) => item.kind === kind);
    for (const item of matching) {
      component.append(option(String(item.component_uid), String(item.name)));
    }
    component.disabled = mode.value !== "fixed";
    mode.addEventListener(
      "change",
      () => {
        component.disabled = mode.value !== "fixed";
      },
      { signal: this.abortController.signal },
    );
    element.append(title, mode, component);
    return { element, controls: { mode, component } };
  }
}

/** @param {string} value @param {string} label */
function option(value, label) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}
