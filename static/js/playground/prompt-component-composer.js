import { PromptAtomEditor } from "../prompts/prompt-atom-editor.js";

/** Own experiment-local atom editing for one exact fixed prompt component. */
export class PromptComponentComposer {
  /** @param {HTMLElement} root @param {{kind: string, componentUid: string, revisionUid: string, candidateUid?: string | null, positiveAtoms?: Array<Record<string, any>>, negativeAtoms?: Array<Record<string, any>>, onChange?: () => void, onReset?: () => void, onSave?: (payload: Record<string, any>, signal: AbortSignal) => Promise<any>, onSaved?: (candidate: Record<string, any>) => void}} options */
  constructor(root, options) {
    this.root = root;
    this.identity = {
      kind: options.kind,
      componentUid: options.componentUid,
      revisionUid: options.revisionUid,
      candidateUid: options.candidateUid || null,
    };
    this.originalPositive = atomValues(options.positiveAtoms);
    this.originalNegative = atomValues(options.negativeAtoms);
    this.onChange = options.onChange || (() => {});
    this.onReset = options.onReset || this.onChange;
    this.onSave = options.onSave || null;
    this.onSaved = options.onSaved || (() => {});
    this.abortController = new AbortController();
    this.request = null;
    this.positive = null;
    this.negative = null;
    this.status = document.createElement("span");
    this.status.className = "prompt-composer-status";
    this.#render();
  }

  value() {
    return {
      kind: this.identity.kind,
      component_uid: this.identity.componentUid,
      revision_uid: this.identity.revisionUid,
      candidate_uid: this.identity.candidateUid,
      positive_atoms: this.positive?.value() || [],
      negative_atoms: this.negative?.value() || [],
    };
  }

  isDirty() {
    const value = this.value();
    return (
      JSON.stringify(value.positive_atoms) !==
        JSON.stringify(this.originalPositive) ||
      JSON.stringify(value.negative_atoms) !==
        JSON.stringify(this.originalNegative)
    );
  }

  reset() {
    this.#createEditors();
    this.identity.candidateUid = null;
    this.status.textContent = "Katalogstand wiederhergestellt";
    this.onReset();
  }

  async save() {
    if (!this.onSave) return null;
    this.request?.abort();
    const request = new AbortController();
    this.request = request;
    this.status.textContent = "Katalog-Test wird gespeichert …";
    try {
      const value = this.value();
      const candidate = await this.onSave(
        {
          component_uid: value.component_uid,
          source_revision_uid: value.revision_uid,
          candidate_type: "manual",
          positive_atoms: value.positive_atoms,
          negative_atoms: value.negative_atoms,
        },
        request.signal,
      );
      this.identity.candidateUid =
        String(candidate.candidate_uid || "") || null;
      this.status.textContent = "Als Katalog-Test gespeichert";
      this.onSaved(candidate);
      return candidate;
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        this.status.textContent =
          "Katalog-Test konnte nicht gespeichert werden";
      return null;
    } finally {
      if (this.request === request) this.request = null;
    }
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const control of this.root.querySelectorAll("input, button")) {
      if (
        control instanceof HTMLInputElement ||
        control instanceof HTMLButtonElement
      )
        control.disabled = busy;
    }
  }

  dispose() {
    this.request?.abort();
    this.abortController.abort();
    this.positive?.dispose();
    this.negative?.dispose();
    this.positive = null;
    this.negative = null;
  }

  #render() {
    this.root.replaceChildren();
    this.root.className = "prompt-component-composer";
    const heading = document.createElement("div");
    heading.className = "prompt-composer-heading";
    const title = document.createElement("strong");
    title.textContent = "Prompt-Atome";
    const actions = document.createElement("div");
    actions.className = "prompt-composer-actions";
    const reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "Auf Katalogstand zurücksetzen";
    reset.addEventListener("click", () => this.reset(), {
      signal: this.abortController.signal,
    });
    const save = document.createElement("button");
    save.type = "button";
    save.textContent = "Als Katalog-Test speichern";
    save.disabled = !this.onSave;
    save.addEventListener("click", () => void this.save(), {
      signal: this.abortController.signal,
    });
    actions.append(reset, save);
    heading.append(title, actions);
    this.root.append(heading, this.status);
    this.#createEditors();
  }

  #createEditors() {
    this.positive?.dispose();
    this.negative?.dispose();
    this.root.querySelector(".prompt-composer-editors")?.remove();
    const editors = document.createElement("div");
    editors.className = "prompt-composer-editors";
    this.positive = new PromptAtomEditor("Positiv", this.originalPositive, () =>
      this.onChange(),
    );
    this.negative = new PromptAtomEditor("Negativ", this.originalNegative, () =>
      this.onChange(),
    );
    editors.append(this.positive.element, this.negative.element);
    this.root.append(editors);
  }
}

/** @param {unknown} values */
function atomValues(values) {
  return Array.isArray(values)
    ? values.map((item) => ({
        text: String(item.text || ""),
        weight: Number(item.weight ?? 1),
      }))
    : [];
}
