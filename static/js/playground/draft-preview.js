import { PromptAtomEditor } from "../prompts/prompt-atom-editor.js";
import { EvidenceCarousel } from "../components/evidence-carousel.js";

/** Own grouped prompt overrides and rendered evidence for one draft. */
export class DraftPreview {
  /** @param {HTMLElement} root @param {HTMLElement} state @param {() => void} [onChange] @param {(url: string) => void} [onImageSelect] @param {((imageUid: string) => HTMLElement) | null} [createGeneratorActions] */
  constructor(
    root,
    state,
    onChange = () => {},
    onImageSelect = () => {},
    createGeneratorActions = null,
  ) {
    this.root = root;
    this.state = state;
    this.onChange = onChange;
    this.abortController = new AbortController();
    this.draft = null;
    this.draftUid = "";
    /** @type {Array<{scope: "positive" | "negative", editor: PromptAtomEditor}>} */
    this.editors = [];
    this.positiveSnapshot = document.createElement("pre");
    this.negativeSnapshot = document.createElement("pre");
    this.evidenceRoot = document.createElement("section");
    this.evidenceCarousel = new EvidenceCarousel({
      className: "draft-evidence-carousel",
      onSelect: (item) => onImageSelect(String(item.image_url || "")),
      createGeneratorActions: createGeneratorActions || undefined,
    });
  }

  /** @param {Record<string, any>} draft @param {string} draftUid */
  render(draft, draftUid) {
    this.clear();
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
    const groups = document.createElement("div");
    groups.className = "draft-component-groups";
    for (const group of draft.groups || []) groups.append(this.#group(group));
    const snapshots = document.createElement("section");
    snapshots.className = "draft-rendered-snapshots";
    const snapshotTitle = document.createElement("h3");
    snapshotTitle.textContent = "Serverseitig gerenderter Prompt";
    snapshots.append(
      snapshotTitle,
      labeledSnapshot("Positiv", this.positiveSnapshot),
      labeledSnapshot("Negativ", this.negativeSnapshot),
    );
    this.evidenceRoot = document.createElement("section");
    this.evidenceRoot.className = "draft-evidence";
    this.evidenceRoot.append(
      evidenceCard("Prompt-ähnlich", "Beispiel wird ermittelt …", "prompt"),
      evidenceCard("Sampler-ähnlich", "Beispiel wird ermittelt …", "sampler"),
    );
    this.root.append(memberships, groups, snapshots, this.evidenceRoot);
    this.renderSnapshots(draft);
    this.#updateState(false);
  }

  /** Clear every visible and retained value for an invalidated draft. */
  clear() {
    this.#disposeEditors();
    this.draft = null;
    this.draftUid = "";
    this.root.replaceChildren();
    this.positiveSnapshot.textContent = "";
    this.negativeSnapshot.textContent = "";
    this.evidenceRoot.replaceChildren();
    this.state.textContent = "Kein gültiger Entwurf";
  }

  /** Return flattened canonical group order for the server renderer. */
  promptPayload() {
    if (!this.editors.length) return null;
    return {
      positive_atoms: this.#atoms("positive"),
      negative_atoms: this.#atoms("negative"),
      loras: Array.isArray(this.draft?.loras)
        ? this.draft.loras.map(generationLoraPayload)
        : [],
    };
  }

  /** @param {Record<string, any>} payload */
  renderSnapshots(payload) {
    this.positiveSnapshot.textContent = String(payload.positive_prompt || "—");
    this.negativeSnapshot.textContent = String(payload.negative_prompt || "—");
  }

  /** @param {Record<string, any>} payload */
  renderEvidence(payload) {
    const prompt = matches(payload.prompt_matches, payload.prompt_match);
    const sampler = matches(payload.sampler_matches, payload.sampler_match);
    const byUid = new Map();
    for (const [kind, items] of [
      ["prompt", prompt],
      ["sampler", sampler],
    ]) {
      for (const item of items) {
        if (!item?.image_uid) continue;
        const current = byUid.get(item.image_uid) || { ...item, badges: [] };
        current.badges.push(
          kind === "prompt" ? "Prompt-ähnlich" : "Sampler-ähnlich",
        );
        byUid.set(item.image_uid, current);
      }
    }
    this.evidenceRoot.replaceChildren();
    if (!byUid.size) {
      this.evidenceRoot.append(
        evidenceCard("Beispiele", "Noch kein passender Bildtreffer.", "empty"),
      );
      return;
    }
    const grouped = [...byUid.values()];
    const promptItems = grouped.filter((item) =>
      item.badges.includes("Prompt-ähnlich"),
    );
    const samplerItems = grouped.filter(
      (item) =>
        item.badges.length === 1 && item.badges.includes("Sampler-ähnlich"),
    );
    if (promptItems.length)
      this.evidenceRoot.append(this.#evidenceGroup(promptItems));
    if (samplerItems.length)
      this.evidenceRoot.append(this.#evidenceGroup(samplerItems));
  }

  /** @param {Record<string, any>} settings */
  generationPayload(settings) {
    if (!this.draft || !this.editors.length) return null;
    const promptSelections = Array.isArray(this.draft.prompt_selections)
      ? this.draft.prompt_selections
      : [];
    const loras = Array.isArray(this.draft.loras)
      ? this.draft.loras
      : Array.isArray(settings.loras)
        ? settings.loras
        : [];
    if (
      !this.draft.source_image_uid &&
      !promptSelections.some((selection) => selection.kind === "character")
    )
      return null;
    return {
      draft_uid: this.draftUid,
      prompt_selections: promptSelections.map((selection) => ({
        kind: selection.kind,
        component_uid: selection.component_uid,
        revision_uid: selection.revision_uid,
      })),
      source_image_uid: this.draft.source_image_uid || null,
      positive_atoms: this.#atoms("positive"),
      negative_atoms: this.#atoms("negative"),
      checkpoint: settings.checkpoint,
      aspect_format: settings.aspect_format,
      resolution_class: settings.resolution_class,
      sampler: settings.sampler,
      loras: loras.map(generationLoraPayload),
    };
  }

  dispose() {
    this.abortController.abort();
    this.evidenceCarousel.dispose();
    this.clear();
  }

  /** @param {Record<string, any>} group */
  #group(group) {
    const section = document.createElement("section");
    section.className = "draft-component-group";
    section.dataset.kind = String(group.kind || "");
    const title = document.createElement("h3");
    title.textContent = String(group.name || group.kind || "Baustein");
    section.append(title);
    for (const [scope, label, values] of [
      ["positive", "Positiv", group.positive_atoms || []],
      ["negative", "Negativ", group.negative_atoms || []],
    ]) {
      const editor = new PromptAtomEditor(label, values, () =>
        this.#updateState(true),
      );
      this.editors.push({ scope, editor });
      section.append(editor.element);
    }
    return section;
  }

  /** @param {"positive" | "negative"} scope */
  #atoms(scope) {
    return this.editors.flatMap((item) =>
      item.scope === scope ? item.editor.value() : [],
    );
  }

  #isEdited() {
    const draft = this.draft || {};
    return (
      JSON.stringify(this.#atoms("positive")) !==
        JSON.stringify(draft.positive_atoms || []) ||
      JSON.stringify(this.#atoms("negative")) !==
        JSON.stringify(draft.negative_atoms || [])
    );
  }

  /** @param {boolean} notify */
  #updateState(notify) {
    const overridden =
      Boolean(this.draft?.draft_overridden) || this.#isEdited();
    this.state.textContent = overridden
      ? "Draft-Override aktiv"
      : "Katalogrevisionen unverändert";
    if (notify) this.onChange();
  }

  #disposeEditors() {
    for (const item of this.editors) item.editor.dispose();
    this.editors = [];
  }

  /** @param {Array<Record<string, any>>} items */
  #evidenceGroup(items) {
    const title = [...new Set(items.flatMap((item) => item.badges))].join(
      " · ",
    );
    const card = evidenceCard(
      title,
      `${items.length} passende Bildbeispiele`,
      "match",
    );
    card.prepend(this.evidenceCarousel.render(items, title));
    return card;
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

/** @param {string} title @param {string} message @param {string} kind */
function evidenceCard(title, message, kind) {
  const card = document.createElement("article");
  card.className = "draft-evidence-card";
  card.dataset.evidenceKind = kind;
  const heading = document.createElement("h3");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.textContent = message;
  card.append(heading, copy);
  return card;
}

/** @param {Record<string, any>} item */
/** @param {unknown} values @param {unknown} fallback */
function matches(values, fallback) {
  if (Array.isArray(values) && values.length) return values;
  return fallback ? [fallback] : [];
}

/** Translate draft display metadata into the generation API contract. */
/** @param {Record<string, any>} lora */
function generationLoraPayload(lora) {
  return {
    name: String(lora.provider_name || lora.name || ""),
    lora_uid: lora.lora_uid || null,
    revision_uid: lora.revision_uid || null,
    model_strength: Number(lora.model_strength ?? 1),
    clip_strength: Number(lora.clip_strength ?? 1),
  };
}
