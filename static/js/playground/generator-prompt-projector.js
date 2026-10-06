import { promptKinds } from "./prompt-mode-editor.js";

const generatorPromptKinds = promptKinds.map(([kind]) => kind);

/** @param {Record<string, any>} promptSetup */
export function imagePromptState(promptSetup) {
  if (!Array.isArray(promptSetup.selections)) {
    throw new Error("Typed Prompt-Selections fehlen.");
  }
  const selectedByKind = selectionsByKind(promptSetup.selections, true, true);
  if (!selectedByKind.has("character")) {
    throw new Error("Character-Prompt-Auswahl fehlt.");
  }
  return completeState(selectedByKind, imagePromptLoras(promptSetup.loras));
}

/** @param {Array<Record<string, any>>} selections */
export function compositionPromptState(selections) {
  if (!Array.isArray(selections)) {
    throw new Error("Typed Composition-Selections fehlen.");
  }
  const selectedByKind = selectionsByKind(selections, false, false);
  if (!selectedByKind.has("character")) {
    throw new Error("Character-Prompt-Auswahl fehlt.");
  }
  return completeState(selectedByKind, []);
}

/** @param {Record<string, any>} selection */
export function scopePromptPatch(selection) {
  const kind = String(selection.kind || "");
  if (!generatorPromptKinds.includes(kind)) {
    throw new Error(`Unbekannte Prompt-Rolle: ${kind || "ohne Kind"}`);
  }
  const componentUid = String(selection.component_uid || "").trim();
  const revisionUid = String(selection.revision_uid || "").trim() || null;
  if (!componentUid) {
    throw new Error(`Prompt-Rolle unvollständig: ${kind}`);
  }
  return {
    selections: [
      {
        kind,
        mode: "fixed",
        component_uid: componentUid,
        revision_uid: revisionUid,
      },
    ],
  };
}

/**
 * @param {Array<Record<string, any>>} selections
 * @param {boolean} requirePosition
 * @param {boolean} allowPosition
 */
function selectionsByKind(selections, requirePosition, allowPosition) {
  const selectedByKind = new Map();
  const positionedSelections = selections
    .map((selection, index) => ({ selection, index }))
    .sort((left, right) => {
      if (!allowPosition) return left.index - right.index;
      const positionDifference =
        Number(left.selection?.position) - Number(right.selection?.position);
      return Number.isFinite(positionDifference) && positionDifference !== 0
        ? positionDifference
        : left.index - right.index;
    });
  for (const { selection } of positionedSelections) {
    const position = selection?.position;
    if (requirePosition && (!Number.isInteger(position) || position < 0)) {
      throw new Error("Prompt-Reihenfolge ist ungültig.");
    }
    const kind = String(selection?.kind || "");
    if (!generatorPromptKinds.includes(kind)) {
      throw new Error(`Unbekannte Prompt-Rolle: ${kind || "ohne Kind"}`);
    }
    if (selectedByKind.has(kind)) {
      throw new Error(`Prompt-Rolle mehrfach vorhanden: ${kind}`);
    }
    const componentUid = String(selection?.component_uid || "").trim();
    const revisionUid = String(selection?.revision_uid || "").trim();
    if (!componentUid || !revisionUid) {
      throw new Error(`Prompt-Rolle unvollständig: ${kind}`);
    }
    selectedByKind.set(kind, {
      kind,
      mode: "fixed",
      component_uid: componentUid,
      revision_uid: revisionUid,
    });
  }
  return selectedByKind;
}

/** @param {Map<string, Record<string, any>>} selectedByKind @param {Array<Record<string, any>>} loras */
function completeState(selectedByKind, loras) {
  return {
    selections: generatorPromptKinds.map(
      (kind) =>
        selectedByKind.get(kind) || {
          kind,
          mode: "off",
          component_uid: null,
          revision_uid: null,
        },
    ),
    loras,
  };
}

/** @param {unknown} loras */
function imagePromptLoras(loras) {
  if (loras === undefined || loras === null) return [];
  if (!Array.isArray(loras)) {
    throw new Error("LoRA-Setup des Bildes ist ungültig.");
  }
  return loras.flatMap((lora) => {
    if (
      !lora ||
      typeof lora !== "object" ||
      typeof lora.model_effective !== "boolean" ||
      typeof lora.clip_effective !== "boolean"
    ) {
      throw new Error("LoRA-Wirksamkeit des Bildes ist nicht verfügbar.");
    }
    if (!lora.model_effective && !lora.clip_effective) return [];
    const modelStrength = lora.model_effective
      ? Number(lora.model_strength)
      : 0;
    const clipStrength = lora.clip_effective ? Number(lora.clip_strength) : 0;
    if (!Number.isFinite(modelStrength) || !Number.isFinite(clipStrength)) {
      throw new Error("LoRA-Stärken des Bildes sind ungültig.");
    }
    return [
      {
        lora_uid: lora.lora_uid,
        revision_uid: lora.revision_uid,
        provider_name: lora.provider_name,
        model_strength: modelStrength,
        clip_strength: clipStrength,
      },
    ];
  });
}
