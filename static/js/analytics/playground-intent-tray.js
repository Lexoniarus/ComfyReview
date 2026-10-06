import { intentFromAnalyticsAction } from "../playground/playground-intent.js";

/** Present tab-local Playground staging without owning domain state. */
export class PlaygroundIntentTray {
  /** @param {HTMLElement} root @param {HTMLElement} toast @param {{read: () => Record<string, any>, merge: (intent: Record<string, any>) => Record<string, any>, stagePromptScope: (scope: {kind: string, component_uid: string, revision_uid?: string | null}) => Record<string, any>, stagePromptComposition: (uid: string) => Record<string, any>, clear: () => void, consumeUrl: () => string}} store @param {{assign: (url: string) => void}} locationRef */
  constructor(root, toast, store, locationRef) {
    this.root = root;
    this.toast = toast;
    this.store = store;
    this.locationRef = locationRef;
    this.abortController = new AbortController();
    this.timer = null;
    this.root.addEventListener(
      "click",
      (event) => {
        const button =
          event.target instanceof Element
            ? event.target.closest("button")
            : null;
        if (!(button instanceof HTMLButtonElement)) return;
        if (button.dataset.intentReset !== undefined) {
          this.store.clear();
          this.render();
        } else if (button.dataset.intentOpen !== undefined) {
          this.locationRef.assign(this.store.consumeUrl());
        }
      },
      { signal: this.abortController.signal },
    );
    this.render();
  }

  /** @param {HTMLElement} source */
  stage(source) {
    const intent = intentFromAnalyticsAction(source);
    if (intent.promptScope) {
      this.store.stagePromptScope(intent.promptScope);
    } else if (intent.promptCompositionUid) {
      this.store.stagePromptComposition(intent.promptCompositionUid);
    } else {
      this.store.merge(intent);
    }
    this.render();
    this.#toast(
      actionMessage(String(source.dataset.playgroundIntent || ""), source),
    );
  }

  render() {
    this.root.replaceChildren();
    const intent = this.store.read();
    const fields = summary(intent);
    this.root.hidden = fields.length === 0;
    if (!fields.length) return;
    const title = document.createElement("strong");
    title.textContent = "Für den Generator vorgemerkt";
    const values = document.createElement("span");
    values.textContent = fields.join(" · ");
    const reset = document.createElement("button");
    reset.type = "button";
    reset.dataset.intentReset = "";
    reset.textContent = "Zurücksetzen";
    const open = document.createElement("button");
    open.type = "button";
    open.dataset.intentOpen = "";
    open.className = "primary-button";
    open.textContent = "Generator öffnen";
    this.root.append(title, values, reset, open);
  }

  dispose() {
    this.abortController.abort();
    if (this.timer !== null) window.clearTimeout(this.timer);
  }

  /** @param {string} text */
  notify(text) {
    this.#toast(text);
  }

  /** @param {string} text */
  #toast(text) {
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.toast.textContent = text;
    this.toast.hidden = false;
    this.timer = window.setTimeout(() => {
      this.toast.hidden = true;
      this.timer = null;
    }, 2800);
  }
}

/** @param {Record<string, any>} intent */
function summary(intent) {
  const fields = [];
  if (intent.promptImageUid) fields.push("Prompt-Setup eines Bildes");
  if (intent.renderImageUid)
    fields.push("Generierungseinstellungen eines Bildes");
  if (intent.promptCompositionUid) fields.push("Prompt-Komposition");
  if (intent.promptScope) fields.push("Prompt-Baustein");
  for (const [key, label] of [
    ["checkpoint", "Checkpoint"],
    ["sampler", "Sampler"],
    ["scheduler", "Scheduler"],
    ["steps_min", "Steps"],
    ["cfg_min", "CFG"],
    ["denoise", "Denoise"],
    ["seed", "Seed"],
    ["aspect_format", "Format"],
    ["resolution_class", "Auflösung"],
  ]) {
    if (intent[key] !== undefined && intent[key] !== "")
      fields.push(`${label} ${intent[key]}`);
  }
  return fields;
}

/** @param {string} kind @param {HTMLElement} source */
function actionMessage(kind, source) {
  if (kind === "scope" || kind === "composition")
    return "Prompt für den Generator vorgemerkt";
  if (kind === "parameter")
    return `${source.dataset.parameter || "Parameter"} für den Generator vorgemerkt`;
  if (kind === "recommendation" || kind === "render_setup")
    return "Gesamtsetup für den Generator vorgemerkt";
  return "Auswahl für den Generator vorgemerkt";
}
