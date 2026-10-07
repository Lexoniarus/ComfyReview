/** Render selectable text-first variant cards without owning business rules. */
export class VariantBoard {
  /** @param {HTMLElement} root @param {{onSelect?: (draftUid: string, selected: boolean) => void, onInspect?: (draftUid: string) => void}} [actions] */
  constructor(root, actions = {}) {
    this.root = root;
    this.onSelect = actions.onSelect || (() => {});
    this.onInspect = actions.onInspect || (() => {});
    this.abortController = new AbortController();
  }

  /** @param {{variants: Array<Record<string, any>>, selectedDraftUids: Set<string>, activeDraftUid: string, stale: boolean, metadata: Record<string, any>}} state */
  render(state) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    this.root.className = "variant-board";
    if (!state.variants.length) {
      const empty = document.createElement("p");
      empty.className = "playground-empty";
      empty.textContent = "Noch keine Varianten vorbereitet.";
      this.root.append(empty);
      return;
    }
    if (state.stale) {
      const warning = document.createElement("p");
      warning.className = "variant-stale-notice";
      warning.setAttribute("role", "status");
      warning.textContent =
        "Das Setup wurde geändert. Diese Varianten bleiben zum Vergleich sichtbar, müssen vor der Generierung aber aktualisiert werden.";
      this.root.append(warning);
    }
    if (state.metadata.notice) {
      const notice = document.createElement("p");
      notice.className = "variant-diversity-notice";
      notice.textContent = state.metadata.notice;
      this.root.append(notice);
    }
    const grid = document.createElement("div");
    grid.className = "variant-card-grid";
    state.variants.forEach((variant, index) =>
      grid.append(this.#card(variant, index, state)),
    );
    this.root.append(grid);
  }

  dispose() {
    this.abortController.abort();
    this.root.replaceChildren();
  }

  /** @param {Record<string, any>} variant @param {number} index @param {{selectedDraftUids: Set<string>, activeDraftUid: string, stale: boolean}} state */
  #card(variant, index, state) {
    const draftUid = String(variant.draft_uid || "");
    const card = document.createElement("article");
    card.className = "variant-card";
    card.dataset.draftUid = draftUid;
    if (state.activeDraftUid === draftUid) card.dataset.active = "true";
    if (state.stale) card.dataset.stale = "true";

    const header = document.createElement("header");
    const selection = document.createElement("label");
    selection.className = "variant-card-selection";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selectedDraftUids.has(draftUid);
    checkbox.setAttribute("aria-label", `Variante ${index + 1} auswählen`);
    checkbox.addEventListener(
      "change",
      () => this.onSelect(draftUid, checkbox.checked),
      { signal: this.abortController.signal },
    );
    const title = document.createElement("strong");
    title.textContent = `Variante ${index + 1}`;
    selection.append(checkbox, title);
    const sampler = document.createElement("span");
    sampler.className = "variant-card-sampler";
    sampler.textContent = samplerSummary(variant);
    header.append(selection, sampler);

    const components = document.createElement("ul");
    components.className = "variant-component-list";
    for (const component of variant.components || []) {
      const item = document.createElement("li");
      item.textContent = `${component.kind}: ${component.name}`;
      components.append(item);
    }
    const prompt = document.createElement("p");
    prompt.className = "variant-prompt-summary";
    prompt.textContent = String(
      variant.positive_prompt || "Kein positiver Prompt",
    );
    const inspect = document.createElement("button");
    inspect.type = "button";
    inspect.textContent = "Prüfen & bearbeiten";
    inspect.addEventListener("click", () => this.onInspect(draftUid), {
      signal: this.abortController.signal,
    });
    card.append(header, components, prompt, inspect);
    return card;
  }
}

/** @param {Record<string, any>} variant */
function samplerSummary(variant) {
  const generation = variant.generation || {};
  return `Seed ${generation.seed ?? variant.seed ?? "—"} · ${generation.steps ?? "—"} Steps · CFG ${generation.cfg ?? "—"}`;
}
