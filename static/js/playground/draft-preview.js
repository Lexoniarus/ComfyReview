import { PromptAtomEditor } from "../prompts/prompt-atom-editor.js";

/** Own the reviewed prompt snapshot and its local draft overrides. */
export class DraftPreview {
  /** @param {HTMLElement} root @param {HTMLElement} state */
  constructor(root, state) {
    this.root = root;
    this.state = state;
    this.abortController = new AbortController();
    /** @type {Record<string, any> | null} */
    this.draft = null;
    this.draftUid = "";
    this.positive = null;
    this.negative = null;
  }

  /** @param {Record<string, any>} draft @param {string} draftUid */
  render(draft, draftUid) {
    this.positive?.dispose();
    this.negative?.dispose();
    this.draft = draft;
    this.draftUid = draftUid;
    this.root.replaceChildren();
    const memberships = document.createElement("div");
    memberships.className = "draft-memberships";
    for (const component of draft.components || []) {
      const badge = document.createElement("span");
      badge.className = "draft-membership";
      badge.textContent = `${component.name} · R${component.latest_revision.revision_number}`;
      memberships.append(badge);
    }
    const fields = document.createElement("div");
    fields.className = "draft-fields";
    this.positive = new PromptAtomEditor(
      "Positive Atome",
      draft.positive_atoms || [],
      () => this.#updateState(),
    );
    this.negative = new PromptAtomEditor(
      "Negative Atome",
      draft.negative_atoms || [],
      () => this.#updateState(),
    );
    fields.append(this.positive.element, this.negative.element);
    this.root.append(memberships, fields);
    this.#updateState();
  }

  /** @param {Record<string, any>} settings */
  generationPayload(settings) {
    if (!this.draft || !this.positive || !this.negative) return null;
    /** @type {Array<Record<string, any>>} */
    const components = Array.isArray(this.draft.components)
      ? this.draft.components
      : [];
    if (!components.some((component) => component.kind === "character")) {
      return null;
    }
    return {
      draft_uid: this.draftUid,
      component_uids: components.map((component) => component.component_uid),
      positive_atoms: this.positive.value(),
      negative_atoms: this.negative.value(),
      checkpoint: settings.checkpoint,
      sampler: settings.sampler,
    };
  }

  /** Release owned prompt listeners. */
  dispose() {
    this.abortController.abort();
    this.positive?.dispose();
    this.negative?.dispose();
    this.draft = null;
    this.positive = null;
    this.negative = null;
  }

  #isEdited() {
    return Boolean(
      this.positive &&
      this.negative &&
      (JSON.stringify(this.positive.value()) !==
        JSON.stringify(this.draft?.positive_atoms || []) ||
        JSON.stringify(this.negative.value()) !==
          JSON.stringify(this.draft?.negative_atoms || [])),
    );
  }

  #updateState() {
    const overridden =
      Boolean(this.draft?.draft_overridden) || this.#isEdited();
    this.state.textContent = overridden
      ? "Draft-Override aktiv"
      : "Katalogrevisionen unverändert";
  }
}
