/** Own the selected-scope summary and its removal actions. */
export class ActiveScopeChips {
  /**
   * @param {HTMLElement} root
   * @param {{onRemove: (uid: string) => void, onClear: () => void}} callbacks
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
        const button = target.closest("[data-active-scope-action]");
        if (!(button instanceof HTMLElement)) return;
        if (button.dataset.activeScopeAction === "clear") {
          this.callbacks.onClear();
        } else if (
          button.dataset.activeScopeAction === "remove" &&
          button.dataset.scopeUid
        ) {
          this.callbacks.onRemove(button.dataset.scopeUid);
        }
      },
      { signal: this.events.signal },
    );
  }

  /** @param {Array<Record<string, unknown>>} facets @param {string[]} selected */
  render(facets, selected) {
    this.root.replaceChildren();
    if (selected.length === 0) {
      this.root.hidden = true;
      return;
    }
    this.root.hidden = false;
    const byUid = new Map(
      facets.map((facet) => [String(facet.component_uid || ""), facet]),
    );
    const label = document.createElement("span");
    label.className = "active-scope-label";
    label.textContent = "Aktiv";
    this.root.append(label);
    for (const uid of selected) {
      const facet = byUid.get(uid);
      const name = String(facet?.name || uid);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "active-scope-chip";
      button.dataset.activeScopeAction = "remove";
      button.dataset.scopeUid = uid;
      button.textContent = `${name} ×`;
      button.setAttribute("aria-label", `Bereich ${name} entfernen`);
      this.root.append(button);
    }
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "active-scope-clear";
    clear.dataset.activeScopeAction = "clear";
    clear.textContent = "Alle entfernen";
    this.root.append(clear);
  }

  /** Release the delegated click listener. */
  dispose() {
    this.events.abort();
  }
}
