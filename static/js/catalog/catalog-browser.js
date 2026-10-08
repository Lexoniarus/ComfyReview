const catalogKinds = [
  ["", "Alle"],
  ["character", "Charakter"],
  ["scene", "Szenen"],
  ["atmosphere", "Atmosphäre"],
  ["lighting", "Licht"],
  ["outfit", "Outfits"],
  ["accessory", "Accessoires"],
  ["pose", "Posen"],
  ["expression", "Ausdrücke"],
  ["framing", "Bildausschnitte"],
  ["camera_angle", "Kamerawinkel"],
  ["optical_effect", "Optische Effekte"],
  ["lora", "LoRAs"],
];

/** Own catalog navigation, search and current list selection. */
export class CatalogBrowser {
  /** @param {HTMLElement} kindsRoot @param {HTMLElement} listRoot @param {HTMLInputElement} search @param {{onSelect: (uid: string, catalogKind: string) => void}} actions */
  constructor(kindsRoot, listRoot, search, actions) {
    this.kindsRoot = kindsRoot;
    this.listRoot = listRoot;
    this.search = search;
    this.actions = actions;
    this.abortController = new AbortController();
    this.kind = "";
    this.selectedUid = "";
    /** @type {Array<Record<string, any>>} */
    this.components = [];
    this.#renderKinds();
    this.search.addEventListener("input", () => this.#renderList(), {
      signal: this.abortController.signal,
    });
  }

  /** @param {Array<Record<string, any>>} components */
  render(components) {
    this.components = components;
    this.#renderList();
  }

  /** @param {string} componentUid */
  select(componentUid) {
    this.selectedUid = componentUid;
    this.#renderList();
  }

  selectedCatalogKind() {
    return this.kind === "lora" ? "lora" : "component";
  }

  /** Release owned navigation and search listeners. */
  dispose() {
    this.abortController.abort();
    this.components = [];
  }

  #renderKinds() {
    this.kindsRoot.replaceChildren();
    for (const [kind, label] of catalogKinds) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "catalog-kind-button";
      button.textContent = label;
      button.setAttribute("aria-current", String(kind === this.kind));
      button.addEventListener(
        "click",
        () => {
          this.kind = kind;
          this.#renderKinds();
          this.#renderList();
        },
        { signal: this.abortController.signal },
      );
      this.kindsRoot.append(button);
    }
  }

  #renderList() {
    this.listRoot.replaceChildren();
    const query = this.search.value.trim().toLocaleLowerCase("de");
    const visible = this.components.filter((component) => {
      if (this.kind && component.kind !== this.kind) return false;
      const searchable = [
        component.name,
        component.component_key,
        ...(component.tags || []),
      ]
        .join(" ")
        .toLocaleLowerCase("de");
      return !query || searchable.includes(query);
    });
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "catalog-empty";
      empty.textContent = "Keine Einträge in dieser Auswahl.";
      this.listRoot.append(empty);
      return;
    }
    for (const component of visible) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "catalog-item";
      button.dataset.archived = String(Boolean(component.archived));
      button.setAttribute(
        "aria-current",
        String(component.component_uid === this.selectedUid),
      );
      const name = document.createElement("span");
      name.className = "catalog-item-name";
      name.textContent = String(component.name);
      const meta = document.createElement("span");
      meta.className = "catalog-item-meta";
      meta.textContent = `R${component.latest_revision.revision_number}${component.archived ? " · archiviert" : ""}`;
      button.append(name, meta);
      button.addEventListener(
        "click",
        () =>
          this.actions.onSelect(
            String(component.component_uid),
            String(component.catalog_kind || "component"),
          ),
        { signal: this.abortController.signal },
      );
      this.listRoot.append(button);
    }
  }
}
