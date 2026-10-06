import { generatorPromptKinds } from "./prompt-kind-contract.js";

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

/** @param {unknown} selections */
export function combinationPromptPatch(selections) {
  if (!Array.isArray(selections) || selections.length === 0) {
    throw new Error("Combination enthält keine Prompt-Auswahlen.");
  }
  const selectedKinds = new Set();
  const projectedSelections = selections.map((selection) => {
    const kind = String(selection?.kind || "");
    if (!generatorPromptKinds.includes(kind)) {
      throw new Error(`Unbekannte Prompt-Rolle: ${kind || "ohne Kind"}`);
    }
    if (selectedKinds.has(kind)) {
      throw new Error(`Prompt-Rolle mehrfach vorhanden: ${kind}`);
    }
    const componentUid = selection?.component_uid;
    if (typeof componentUid !== "string" || !componentUid.trim()) {
      throw new Error(`Prompt-Rolle unvollständig: ${kind}`);
    }
    const revisionUid = selection?.revision_uid;
    if (
      revisionUid !== undefined &&
      revisionUid !== null &&
      (typeof revisionUid !== "string" || !revisionUid.trim())
    ) {
      throw new Error(`Prompt-Revision ungültig: ${kind}`);
    }
    selectedKinds.add(kind);
    return {
      kind,
      mode: "fixed",
      component_uid: componentUid,
      revision_uid: revisionUid ?? null,
    };
  });
  return { selections: projectedSelections };
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
  return loras.map((lora) => {
    if (!lora || typeof lora !== "object") {
      throw new Error("LoRA-Setup des Bildes ist ungültig.");
    }
    const loraUid = String(lora.lora_uid || "").trim();
    const revisionUid = String(lora.revision_uid || "").trim();
    if (!loraUid || !revisionUid) {
      throw new Error("LoRA-Identität des Bildes ist unvollständig.");
    }
    const modelStrength = Number(lora.model_strength);
    const clipStrength = Number(lora.clip_strength);
    if (!Number.isFinite(modelStrength) || !Number.isFinite(clipStrength)) {
      throw new Error("LoRA-Stärken des Bildes sind ungültig.");
    }
    return {
      lora_uid: loraUid,
      revision_uid: revisionUid,
      provider_name: lora.provider_name,
      model_strength: modelStrength,
      clip_strength: clipStrength,
    };
  });
}
