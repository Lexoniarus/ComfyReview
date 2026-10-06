import { LoraStackEditor } from "../settings/lora-stack-editor.js";

const promptKinds = [
  ["character", "Charakter"],
  ["scene", "Szene"],
  ["outfit", "Outfit"],
  ["pose", "Pose"],
  ["expression", "Ausdruck"],
  ["lighting", "Licht"],
  ["modifier", "Modifier"],
];

/** Own fixed, random and disabled prompt-role controls plus catalog evidence. */
export class PromptModeEditor {
  /** @param {HTMLElement} root @param {() => void} [onChange] @param {{loadComponent?: (uid: string, signal: AbortSignal) => Promise<any>, onImageSelect?: (url: string) => void}} [evidence] */
  constructor(root, onChange = () => {}, evidence = {}) {
    this.root = root;
    this.abortController = new AbortController();
    this.onChange = typeof onChange === "function" ? onChange : () => {};
    this.loadComponent = evidence.loadComponent || null;
    this.onImageSelect = evidence.onImageSelect || (() => {});
    /** @type {Map<string, {mode: HTMLSelectElement, component: HTMLSelectElement, evidence: HTMLElement}>} */
    this.rows = new Map();
    /** @type {Map<string, any>} */
    this.cache = new Map();
    /** @type {Map<string, AbortController>} */
    this.requests = new Map();
    this.loras = null;
    /** @type {Array<Record<string, any>>} */
    this.loraDefinitions = [];
  }

  /** @param {Array<Record<string, any>>} components @param {Array<Record<string, any>>} [loraDefinitions] */
  render(components, loraDefinitions = []) {
    this.#cancelRequests();
    this.root.replaceChildren();
    this.rows.clear();
    const list = document.createElement("div");
    list.className = "prompt-mode-list";
    for (const [kind, label] of promptKinds) {
      const row = this.#row(kind, label, components);
      list.append(row.element);
      this.rows.set(kind, row.controls);
      void this.#refresh(kind);
    }
    const loraRoot = document.createElement("section");
    loraRoot.className = "prompt-lora-layer";
    const heading = document.createElement("div");
    heading.className = "prompt-lora-heading";
    const title = document.createElement("h3");
    title.textContent = "LoRAs";
    const note = document.createElement("p");
    note.textContent =
      "Eigene Prompt-Ebene mit Revision, Triggern und getrennten Model-/CLIP-Gewichten.";
    heading.append(title, note);
    const editorRoot = document.createElement("div");
    loraRoot.append(heading, editorRoot);
    this.loraDefinitions = loraDefinitions;
    this.loras?.dispose();
    this.loras = new LoraStackEditor(editorRoot, () => this.onChange());
    this.loras.render([], loraDefinitions);
    this.root.append(list, loraRoot);
  }

  /** Return the complete API selection intent. */
  value() {
    return {
      selections: promptKinds.map(([kind]) => {
        const row = this.rows.get(kind);
        return {
          kind,
          mode: row?.mode.value || "random",
          component_uid:
            row?.mode.value === "fixed" ? row.component.value : null,
        };
      }),
      loras: this.loras?.value() || [],
    };
  }

  /** Restore a complete saved UI state after the catalog has rendered. @param {{selections?: Array<Record<string, any>>, loras?: Array<Record<string, any>>}} state */
  applyState(state) {
    const rejected = [];
    const selections = Array.isArray(state.selections) ? state.selections : [];
    for (const selection of selections) {
      const kind = String(selection.kind || "");
      const row = this.rows.get(kind);
      if (!row) continue;
      const mode = String(selection.mode || "");
      if (![...row.mode.options].some((option) => option.value === mode)) {
        rejected.push(kind);
        continue;
      }
      const componentUid = String(selection.component_uid || "");
      if (
        mode === "fixed" &&
        ![...row.component.options].some(
          (option) => option.value === componentUid,
        )
      ) {
        rejected.push(kind);
        continue;
      }
      row.mode.value = mode;
      if (mode === "fixed") row.component.value = componentUid;
      row.component.disabled = mode !== "fixed";
      void this.#refresh(kind);
    }
    if (this.#applyLoras(state.loras)) rejected.push("loras");
    return rejected;
  }

  /** @param {{componentUids?: string[], loras?: Array<Record<string, any>>}} intent */
  applyIntent(intent) {
    const requested = new Set(intent.componentUids || []);
    for (const [kind, row] of this.rows) {
      const selected = Array.from(row.component.options).find((candidate) =>
        requested.has(candidate.value),
      );
      if (!selected) continue;
      row.component.value = selected.value;
      row.mode.value = "fixed";
      row.component.disabled = false;
      void this.#refresh(kind);
    }
    return this.#applyLoras(intent.loras) ? ["loras"] : [];
  }

  /** @param {unknown} loras */
  #applyLoras(loras) {
    if (!Array.isArray(loras)) return false;
    this.loras?.render(loras, this.loraDefinitions);
    return loras.some((requestedLora) => {
      const definition = this.loraDefinitions.find(
        (candidate) => candidate.lora_uid === requestedLora.lora_uid,
      );
      return !definition || definition.available === false;
    });
  }

  /** Show server-resolved random selections after draft creation. @param {Array<Record<string, any>>} components */
  showResolvedComponents(components) {
    for (const component of components || []) {
      const kind = String(component.kind || "");
      const row = this.rows.get(kind);
      if (row?.mode.value === "random")
        void this.#loadInto(kind, String(component.component_uid || ""));
    }
  }

  dispose() {
    this.abortController.abort();
    this.#cancelRequests();
    this.loras?.dispose();
    this.loras = null;
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
    for (const item of components.filter((item) => item.kind === kind))
      component.append(option(String(item.component_uid), String(item.name)));
    component.disabled = mode.value !== "fixed";
    const evidence = document.createElement("div");
    evidence.className = "prompt-reference";
    mode.addEventListener(
      "change",
      () => {
        component.disabled = mode.value !== "fixed";
        void this.#refresh(kind);
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    component.addEventListener(
      "change",
      () => {
        void this.#refresh(kind);
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    element.append(title, mode, component, evidence);
    return { element, controls: { mode, component, evidence } };
  }

  /** @param {string} kind */
  async #refresh(kind) {
    const row = this.rows.get(kind);
    if (!row) return;
    this.requests.get(kind)?.abort();
    if (row.mode.value === "off")
      return renderMessage(row.evidence, "Nicht aktiv");
    if (row.mode.value === "random")
      return renderMessage(row.evidence, "Wird beim Entwurf ausgewählt");
    await this.#loadInto(kind, row.component.value);
  }

  /** @param {string} kind @param {string} uid */
  async #loadInto(kind, uid) {
    const row = this.rows.get(kind);
    if (!row || !uid)
      return renderMessage(row?.evidence, "Kein Katalogeintrag gewählt");
    const cached = this.cache.get(uid);
    if (cached) return this.#renderEvidence(row.evidence, cached);
    if (!this.loadComponent)
      return renderMessage(row.evidence, "Referenz nicht verfügbar");
    this.requests.get(kind)?.abort();
    const controller = new AbortController();
    this.requests.set(kind, controller);
    renderMessage(row.evidence, "Referenz wird geladen …");
    try {
      const payload = await this.loadComponent(uid, controller.signal);
      this.cache.set(uid, payload);
      this.#renderEvidence(row.evidence, payload);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        renderMessage(row.evidence, "Referenz konnte nicht geladen werden");
    } finally {
      if (this.requests.get(kind) === controller) this.requests.delete(kind);
    }
  }

  /** @param {HTMLElement} root @param {Record<string, any>} component */
  #renderEvidence(root, component) {
    root.replaceChildren();
    const images = Array.isArray(component.top_images)
      ? component.top_images
      : [];
    const heading = document.createElement("strong");
    heading.textContent = `${component.name || "Katalogeintrag"} · ${component.kind || ""}`;
    if (!images.length) {
      const empty = document.createElement("span");
      empty.textContent = "Noch kein sichtbares Referenzbild";
      root.append(heading, empty);
      return;
    }
    const image = images[0];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-reference-image";
    const img = document.createElement("img");
    img.src = String(image.image_url || "");
    img.alt = `Referenz für ${component.name || "Prompt-Baustein"}`;
    button.append(img);
    button.addEventListener(
      "click",
      () => this.onImageSelect(String(image.image_url || "")),
      { signal: this.abortController.signal },
    );
    const meta = document.createElement("span");
    meta.textContent = `${Number(image.average_rating || 0).toFixed(2)} Bewertung · ${Number(image.rating_count || 0)} Belege`;
    root.append(heading, button, meta);
  }

  #cancelRequests() {
    for (const request of this.requests.values()) request.abort();
    this.requests.clear();
  }
}

/** @param {HTMLElement | undefined} root @param {string} text */
function renderMessage(root, text) {
  if (!root) return;
  root.replaceChildren();
  const message = document.createElement("span");
  message.textContent = text;
  root.append(message);
}

/** @param {string} value @param {string} label */
function option(value, label) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}
