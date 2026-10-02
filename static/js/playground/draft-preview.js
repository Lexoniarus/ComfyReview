import { PromptAtomEditor } from "../prompts/prompt-atom-editor.js";

/** Own the reviewed prompt snapshot and its local draft overrides. */
export class DraftPreview {
  /** @param {HTMLElement} root @param {HTMLElement} state @param {() => void} [onChange] */
  constructor(root, state, onChange = () => {}) {
    this.root = root;
    this.state = state;
    this.onChange = onChange;
    this.abortController = new AbortController();
    /** @type {Record<string, any> | null} */
    this.draft = null;
    this.draftUid = "";
    this.positive = null;
    this.negative = null;
    this.positiveSnapshot = document.createElement("pre");
    this.negativeSnapshot = document.createElement("pre");
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
      () => this.#updateState(true),
    );
    this.negative = new PromptAtomEditor(
      "Negative Atome",
      draft.negative_atoms || [],
      () => this.#updateState(true),
    );
    fields.append(this.positive.element, this.negative.element);
    const snapshots = document.createElement("section");
    snapshots.className = "draft-rendered-snapshots";
    const snapshotTitle = document.createElement("h3");
    snapshotTitle.textContent = "Serverseitig gerenderter Prompt";
    snapshots.append(
      snapshotTitle,
      labeledSnapshot("Positiv", this.positiveSnapshot),
      labeledSnapshot("Negativ", this.negativeSnapshot),
    );
    this.root.append(memberships, fields, snapshots);
    this.renderSnapshots(draft);
    this.#updateState(false);
  }

  /** Return only the structured values accepted by the server renderer. */
  promptPayload() {
    if (!this.positive || !this.negative) return null;
    return {
      positive_atoms: this.positive.value(),
      negative_atoms: this.negative.value(),
    };
  }

  /** @param {Record<string, any>} payload */
  renderSnapshots(payload) {
    this.positiveSnapshot.textContent = String(payload.positive_prompt || "—");
    this.negativeSnapshot.textContent = String(payload.negative_prompt || "—");
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

  /** @param {boolean} notify */
  #updateState(notify) {
    const overridden =
      Boolean(this.draft?.draft_overridden) || this.#isEdited();
    this.state.textContent = overridden
      ? "Draft-Override aktiv"
      : "Katalogrevisionen unverändert";
    if (notify && this.positive && this.negative) this.onChange();
  }
}

/** @param {string} label @param {HTMLElement} value */
function labeledSnapshot(label, value) {
  const wrapper = document.createElement("div");
  const heading = document.createElement("h4");
  heading.textContent = label;
  wrapper.append(heading, value);
  return wrapper;
}
