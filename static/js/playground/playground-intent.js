const numericFields = [
  "seed",
  "steps_min",
  "steps_max",
  "cfg_min",
  "cfg_max",
  "denoise",
];

/** @typedef {{kind: string, component_uid: string, revision_uid?: string | null}} PromptScopeSource */
/** @typedef {{kind: string, component_uid: string, revision_uid?: string | null}} PromptCombinationSelection */
/** @typedef {{selections: PromptCombinationSelection[], loras: Record<string, unknown>[]}} PromptCombinationPayload */
/** @typedef {{checkpoint?: string, sampler?: string, scheduler?: string, aspectFormat?: string, resolutionClass?: string, seedMode?: string, seed?: number, steps_min?: number, steps_max?: number, cfg_min?: number, cfg_max?: number, denoise?: number}} RenderSettingsIntent */
/** @typedef {{kind: "image-prompt", imageUid: string} | {kind: "image-render", imageUid: string} | {kind: "composition", compositionUid: string} | {kind: "scope", scope: PromptScopeSource} | {kind: "combination", selections: PromptCombinationSelection[] | PromptCombinationPayload} | {kind: "render-settings", settings: RenderSettingsIntent} | {kind: "parameter", parameter: string, value: string}} GeneratorHandoff */
/** @typedef {RenderSettingsIntent & {promptCompositionUid?: string, promptScope?: PromptScopeSource, promptCombination?: PromptCombinationSelection[] | PromptCombinationPayload, promptImageUid?: string, renderImageUid?: string}} PlaygroundIntent */

/** @param {HTMLElement} element @returns {GeneratorHandoff | null} */
export function intentFromAnalyticsAction(element) {
  const kind = String(element.dataset.playgroundIntent || "");
  if (kind === "best_image_prompt") {
    const imageUid = text(element.dataset.imageUid);
    return imageUid ? { kind: "image-prompt", imageUid } : null;
  }
  if (kind === "scope") {
    if (!element.dataset.promptKind || !element.dataset.componentUid)
      return null;
    return {
      kind: "scope",
      scope: {
        kind: text(element.dataset.promptKind),
        component_uid: text(element.dataset.componentUid),
        revision_uid: text(element.dataset.revisionUid) || null,
      },
    };
  }
  if (kind === "composition") {
    return {
      kind: "composition",
      compositionUid: text(element.dataset.compositionUid),
    };
  }
  if (kind === "parameter") {
    return {
      kind: "parameter",
      parameter: text(element.dataset.parameter),
      value: text(element.dataset.value),
    };
  }
  if (kind === "recommendation") {
    return {
      kind: "render-settings",
      settings: settingsIntent(jsonRecord(element.dataset.recommendation)),
    };
  }
  if (kind === "render_setup") {
    return {
      kind: "render-settings",
      settings: settingsIntent(jsonRecord(element.dataset.renderSetup)),
    };
  }
  return null;
}

/** @param {GeneratorHandoff} handoff */
export function playgroundIntentUrl(handoff) {
  const intent = handoffProjection(handoff);
  const query = new URLSearchParams();
  /** @type {Record<string, unknown>} */
  const intentValues = intent;
  set(query, "prompt_composition", intent.promptCompositionUid);
  if (intent.promptScope)
    set(query, "prompt_scope", JSON.stringify(intent.promptScope));
  if (intent.promptCombination)
    set(query, "prompt_combination", JSON.stringify(intent.promptCombination));
  set(query, "prompt_image", intent.promptImageUid);
  set(query, "render_image", intent.renderImageUid);
  set(query, "checkpoint", intent.checkpoint);
  set(query, "sampler", intent.sampler);
  set(query, "scheduler", intent.scheduler);
  set(query, "aspect_format", intent.aspectFormat);
  set(query, "resolution_class", intent.resolutionClass);
  set(query, "seed_mode", intent.seedMode);
  for (const field of numericFields) set(query, field, intentValues[field]);
  const suffix = query.toString();
  return `/playground/generator${suffix ? `?${suffix}` : ""}`;
}

/** @param {string} search @returns {PlaygroundIntent} */
export function readPlaygroundIntent(search) {
  const query = new URLSearchParams(search);
  /** @type {Record<string, any>} */
  const intent = {
    checkpoint: text(query.get("checkpoint")),
    sampler: text(query.get("sampler")),
    scheduler: text(query.get("scheduler")),
    aspectFormat: text(query.get("aspect_format")),
    resolutionClass: text(query.get("resolution_class")),
    seedMode: text(query.get("seed_mode")),
  };
  if (query.has("prompt_composition"))
    intent.promptCompositionUid = text(query.get("prompt_composition"));
  if (query.has("prompt_scope")) {
    const scope = record(json(query.get("prompt_scope")));
    intent.promptScope = {
      kind: text(scope.kind),
      component_uid: text(scope.component_uid),
      revision_uid: text(scope.revision_uid) || null,
    };
  }
  if (query.has("prompt_combination")) {
    intent.promptCombination =
      json(query.get("prompt_combination")) ?? query.get("prompt_combination");
  }
  if (query.has("prompt_image"))
    intent.promptImageUid = text(query.get("prompt_image"));
  if (query.has("render_image"))
    intent.renderImageUid = text(query.get("render_image"));
  for (const field of numericFields) {
    if (!query.has(field)) continue;
    const value = Number(query.get(field));
    if (Number.isFinite(value)) intent[field] = value;
  }
  return intent;
}

/** Own direct navigation from every source surface to the Generator. */
export class GeneratorHandoffNavigator {
  /** @param {{assign: (url: string) => void}} locationRef */
  constructor(locationRef) {
    this.locationRef = locationRef;
  }

  /** @param {HTMLElement} element */
  open(element) {
    const handoff = intentFromAnalyticsAction(element);
    if (handoff) this.openIntent(handoff);
  }

  /** @param {GeneratorHandoff} handoff */
  openIntent(handoff) {
    this.locationRef.assign(playgroundIntentUrl(handoff));
  }
}

/** Own removal of an applied handoff while preserving unrelated URL state. */
export class GeneratorHandoffUrlCleaner {
  /** @param {{href: string}} locationRef @param {{state: unknown, replaceState: (state: unknown, title: string, url?: string | URL | null) => void}} historyRef */
  constructor(locationRef, historyRef) {
    this.locationRef = locationRef;
    this.historyRef = historyRef;
  }

  removeHandoff() {
    const url = new URL(this.locationRef.href);
    let changed = false;
    for (const key of [
      "prompt_composition",
      "prompt_scope",
      "prompt_combination",
      "prompt_image",
      "render_image",
      "checkpoint",
      "sampler",
      "scheduler",
      "aspect_format",
      "resolution_class",
      "seed_mode",
      ...numericFields,
    ]) {
      if (url.searchParams.has(key)) {
        url.searchParams.delete(key);
        changed = true;
      }
    }
    if (!changed) return false;
    const suffix = `${url.pathname}${url.search}${url.hash}`;
    this.historyRef.replaceState(this.historyRef.state, "", suffix);
    return true;
  }
}

/** @param {string} parameter @param {string} value */
function parameterIntent(parameter, value) {
  if (["checkpoint", "sampler", "scheduler"].includes(parameter)) {
    return { [parameter]: value };
  }
  if (parameter === "aspect_format") return { aspectFormat: value };
  if (parameter === "resolution_class") return { resolutionClass: value };
  const number = Number(value);
  if (!Number.isFinite(number)) return {};
  if (parameter === "steps") return { steps_min: number, steps_max: number };
  if (parameter === "cfg") return { cfg_min: number, cfg_max: number };
  if (parameter === "denoise") return { denoise: number };
  return {};
}

/** @param {GeneratorHandoff} handoff @returns {PlaygroundIntent} */
function handoffProjection(handoff) {
  if (handoff.kind === "image-prompt") {
    return { promptImageUid: text(handoff.imageUid) };
  }
  if (handoff.kind === "image-render") {
    return { renderImageUid: text(handoff.imageUid) };
  }
  if (handoff.kind === "composition") {
    return { promptCompositionUid: text(handoff.compositionUid) };
  }
  if (handoff.kind === "scope") return { promptScope: handoff.scope };
  if (handoff.kind === "combination") {
    return { promptCombination: handoff.selections };
  }
  if (handoff.kind === "render-settings") return handoff.settings;
  if (handoff.kind === "parameter") {
    return parameterIntent(handoff.parameter, handoff.value);
  }
  return {};
}

/** @param {Record<string, any>} item */
function settingsIntent(item) {
  const stage = Array.isArray(item.stages) ? record(item.stages[0]) : item;
  return {
    checkpoint: text(item.checkpoint),
    sampler: text(stage.sampler),
    scheduler: text(stage.scheduler),
    steps_min: finite(stage.steps),
    steps_max: finite(stage.steps),
    cfg_min: finite(stage.cfg),
    cfg_max: finite(stage.cfg),
    denoise: finite(stage.denoise),
  };
}

/** @param {unknown} value @returns {Record<string, any>} */
function record(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

/** @param {URLSearchParams} query @param {string} key @param {unknown} value */
function set(query, key, value) {
  if (value !== null && value !== undefined && String(value).trim()) {
    query.set(key, String(value));
  }
}

/** @param {unknown} value */
function finite(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}

/** @param {unknown} value */
function text(value) {
  return String(value || "").trim();
}

/** @param {unknown} value @returns {Record<string, any>} */
function jsonRecord(value) {
  return record(json(value));
}

/** @param {unknown} value */
function json(value) {
  try {
    return JSON.parse(String(value || ""));
  } catch {
    return null;
  }
}
