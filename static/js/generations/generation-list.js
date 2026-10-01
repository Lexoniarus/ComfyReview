/** @type {Record<string, string>} */
const lifecycleLabels = {
  prepared: "Vorbereitet",
  submitting: "Wird übergeben",
  submitted: "Übergeben",
  running: "Läuft",
  completed: "Abgeschlossen",
  failed: "Fehlgeschlagen",
  cancelled: "Abgebrochen",
  reconciliation_required: "Abgleich nötig",
};

/** Own lifecycle filtering and selection for persisted generations. */
export class GenerationList {
  /** @param {HTMLElement} root @param {HTMLSelectElement} statusFilter @param {{onSelect: (uid: string) => void, onFilter: () => void}} actions */
  constructor(root, statusFilter, actions) {
    this.root = root;
    this.statusFilter = statusFilter;
    this.actions = actions;
    this.abortController = new AbortController();
    this.selectedUid = "";
    this.statusFilter.addEventListener(
      "change",
      () => this.actions.onFilter(),
      {
        signal: this.abortController.signal,
      },
    );
  }

  /** Return the selected persisted lifecycle filter. */
  status() {
    return this.statusFilter.value;
  }

  /** @param {Array<Record<string, any>>} generations */
  render(generations) {
    this.root.replaceChildren();
    if (!generations.length) {
      const empty = document.createElement("p");
      empty.className = "generation-empty";
      empty.textContent = "Keine Generierungen in diesem Status.";
      this.root.append(empty);
      return;
    }
    for (const generation of generations) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "generation-item";
      button.dataset.status = String(generation.status);
      button.dataset.generationUid = String(generation.generation_uid);
      button.setAttribute(
        "aria-current",
        String(generation.generation_uid === this.selectedUid),
      );
      const heading = document.createElement("span");
      heading.className = "generation-item-heading";
      heading.textContent = shortUid(String(generation.generation_uid));
      const status = document.createElement("span");
      status.className = "generation-status-badge";
      status.textContent = lifecycleLabel(String(generation.status));
      const meta = document.createElement("span");
      meta.className = "generation-item-meta";
      meta.textContent = `${generation.model || "Ohne Modell"} · ${generation.output_count || 0} Outputs`;
      button.append(heading, status, meta);
      button.addEventListener(
        "click",
        () => this.actions.onSelect(String(generation.generation_uid)),
        { signal: this.abortController.signal },
      );
      this.root.append(button);
    }
  }

  /** @param {string} generationUid */
  select(generationUid) {
    this.selectedUid = generationUid;
    const items = /** @type {NodeListOf<HTMLElement>} */ (
      this.root.querySelectorAll(".generation-item")
    );
    for (const item of items) {
      item.setAttribute(
        "aria-current",
        String(item.dataset.generationUid === generationUid),
      );
    }
  }

  /** Release owned filter and selection listeners. */
  dispose() {
    this.abortController.abort();
    this.root.replaceChildren();
  }
}

/** @param {string} status */
export function lifecycleLabel(status) {
  return lifecycleLabels[status] || status || "Unbekannt";
}

/** @param {string} uid */
export function shortUid(uid) {
  return uid.length > 18 ? `${uid.slice(0, 8)}…${uid.slice(-6)}` : uid;
}
