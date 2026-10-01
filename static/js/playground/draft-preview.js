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
    this.abortController.abort();
    this.abortController = new AbortController();
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
    this.positive = this.#promptField(
      "Positiver Prompt",
      "positive",
      String(draft.positive_prompt || ""),
    );
    this.negative = this.#promptField(
      "Negativer Prompt",
      "negative",
      String(draft.negative_prompt || ""),
    );
    fields.append(this.positive.wrapper, this.negative.wrapper);
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
    const character = components.find(
      (component) => component.kind === "character",
    );
    if (!character) return null;
    const edited = this.#isEdited();
    return {
      draft_uid: this.draftUid,
      character_component_uid: character.component_uid,
      positive_prompt: this.positive.control.value,
      negative_prompt: this.negative.control.value,
      revision_uids: this.draft.revision_uids || [],
      draft_overridden: Boolean(this.draft.draft_overridden) || edited,
      checkpoint: settings.checkpoint,
      sampler: settings.sampler,
    };
  }

  /** Release owned prompt listeners. */
  dispose() {
    this.abortController.abort();
    this.draft = null;
    this.positive = null;
    this.negative = null;
  }

  /** @param {string} label @param {string} scope @param {string} value */
  #promptField(label, scope, value) {
    const wrapper = document.createElement("label");
    wrapper.className = "draft-field";
    wrapper.append(document.createTextNode(label));
    const control = document.createElement("textarea");
    control.dataset.prompt = scope;
    control.value = value;
    control.addEventListener("input", () => this.#updateState(), {
      signal: this.abortController.signal,
    });
    wrapper.append(control);
    return { wrapper, control, original: value };
  }

  #isEdited() {
    return Boolean(
      this.positive &&
      this.negative &&
      (this.positive.control.value !== this.positive.original ||
        this.negative.control.value !== this.negative.original),
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
