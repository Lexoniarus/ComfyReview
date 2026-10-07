import { DraftPreview, generationPromptGroups } from "./draft-preview.js";

/** Own focused inspection and local atom editing for one concrete variant. */
export class VariantInspector {
  /** @param {HTMLElement} root @param {HTMLElement} state @param {() => void} [onChange] @param {(url: string) => void} [onImageSelect] @param {((imageUid: string) => HTMLElement) | null} [createGeneratorActions] */
  constructor(
    root,
    state,
    onChange = () => {},
    onImageSelect = () => {},
    createGeneratorActions = null,
  ) {
    this.variant = null;
    this.preview = new DraftPreview(
      root,
      state,
      onChange,
      onImageSelect,
      createGeneratorActions,
    );
  }

  /** @param {Record<string, any>} variant */
  render(variant) {
    this.variant = variant;
    this.preview.render(variant, String(variant.draft_uid || ""));
  }

  clear() {
    this.variant = null;
    this.preview.clear();
  }

  promptPayload() {
    return this.preview.promptPayload();
  }

  /** @param {Record<string, any>} payload */
  renderSnapshots(payload) {
    this.preview.renderSnapshots(payload);
  }

  /** @param {Record<string, any>} payload */
  renderEvidence(payload) {
    this.preview.renderEvidence(payload);
  }

  generationPayload() {
    if (!this.variant) return null;
    return this.preview.generationPayload(generationSettings(this.variant));
  }

  dispose() {
    this.variant = null;
    this.preview.dispose();
  }
}

/** Build the reviewed one-job payload for an untouched concrete variant. @param {Record<string, any>} variant */
export function variantGenerationPayload(variant) {
  const generation = generationSettings(variant);
  const promptSelections = Array.isArray(variant.prompt_selections)
    ? variant.prompt_selections
    : [];
  const promptGroups = Array.isArray(variant.prompt_groups)
    ? variant.prompt_groups
    : [];
  return {
    draft_uid: String(variant.draft_uid || ""),
    prompt_selections: promptSelections.map(promptSelection),
    prompt_groups: generationPromptGroups(
      variant.source_image_uid,
      promptGroups.map(promptGroup),
    ),
    source_image_uid: variant.source_image_uid || null,
    positive_atoms: atomValues(variant.positive_atoms),
    negative_atoms: atomValues(variant.negative_atoms),
    checkpoint: generation.checkpoint,
    aspect_format: generation.aspect_format,
    resolution_class: generation.resolution_class,
    sampler: generation.sampler,
    loras: (variant.loras || []).map(generationLora),
  };
}

/** Rehydrate one edited payload for later inspection. @param {Record<string, any>} variant @param {Record<string, any>} payload */
export function variantWithReviewedPayload(variant, payload) {
  const promptGroups = Array.isArray(payload.prompt_groups)
    ? payload.prompt_groups
    : [];
  const loraGroups = (variant.groups || []).filter(
    /** @param {Record<string, any>} group */ (group) => group.kind === "lora",
  );
  return {
    ...variant,
    prompt_groups: promptGroups,
    groups: [...promptGroups, ...loraGroups],
    positive_atoms: atomValues(payload.positive_atoms),
    negative_atoms: atomValues(payload.negative_atoms),
  };
}

/** @param {Record<string, any>} variant */
function generationSettings(variant) {
  const generation = variant.generation || {};
  const steps = Number(generation.steps ?? 1);
  const cfg = Number(generation.cfg ?? 1);
  return {
    checkpoint: String(generation.checkpoint || ""),
    aspect_format: String(generation.aspect_format || "1:1"),
    resolution_class: String(generation.resolution_class || "1080"),
    sampler: {
      seed: Number(generation.seed ?? variant.seed ?? 0),
      steps,
      cfg,
      sampler: String(generation.sampler || ""),
      scheduler: String(generation.scheduler || ""),
      denoise: Number(generation.denoise ?? 1),
      batch_runs: 1,
      randomize_seed: false,
      steps_max: steps,
      cfg_max: cfg,
      cfg_step: 0.1,
    },
  };
}

/** @param {Record<string, any>} selection */
function promptSelection(selection) {
  return {
    kind: String(selection.kind || ""),
    component_uid: String(selection.component_uid || ""),
    revision_uid: String(selection.revision_uid || ""),
  };
}

/** @param {Record<string, any>} group */
function promptGroup(group) {
  return {
    ...promptSelection(group),
    candidate_uid: group.candidate_uid || null,
    positive_atoms: atomValues(group.positive_atoms),
    negative_atoms: atomValues(group.negative_atoms),
  };
}

/** @param {unknown} atoms */
function atomValues(atoms) {
  return Array.isArray(atoms)
    ? atoms.map((atom) => ({
        text: String(atom.text || ""),
        weight: Number(atom.weight ?? 1),
      }))
    : [];
}

/** @param {Record<string, any>} lora */
function generationLora(lora) {
  return {
    name: String(lora.provider_name || lora.name || ""),
    lora_uid: lora.lora_uid || null,
    revision_uid: lora.revision_uid || null,
    model_strength: Number(lora.model_strength ?? 1),
    clip_strength: Number(lora.clip_strength ?? 1),
  };
}
