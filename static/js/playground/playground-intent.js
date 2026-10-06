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
/** @typedef {{componentUids?: string[], revisionUids?: string[], compositionUid?: string, promptCompositionUid?: string, promptScope?: PromptScopeSource, promptCombination?: PromptCombinationSelection[], imageUid?: string, promptImageUid?: string, renderImageUid?: string, loras?: any[], checkpoint?: string, sampler?: string, scheduler?: string, aspectFormat?: string, resolutionClass?: string, seedMode?: string, seed?: number, steps_min?: number, steps_max?: number, cfg_min?: number, cfg_max?: number, denoise?: number}} PlaygroundIntent */

/** @param {HTMLElement} element @returns {PlaygroundIntent} */
export function intentFromAnalyticsAction(element) {
  const kind = String(element.dataset.playgroundIntent || "");
  if (kind === "scope") {
    if (element.dataset.promptKind && element.dataset.componentUid) {
      return {
        promptScope: {
          kind: text(element.dataset.promptKind),
          component_uid: text(element.dataset.componentUid),
          revision_uid: text(element.dataset.revisionUid) || null,
        },
      };
    }
    return {
      componentUids: [
        ...values(element.dataset.componentUid),
        ...jsonValues(element.dataset.componentUids),
      ],
    };
  }
  if (kind === "composition") {
    return {
      promptCompositionUid: text(element.dataset.compositionUid),
    };
  }
  if (kind === "image") {
    return { imageUid: text(element.dataset.imageUid) };
  }
  if (kind === "parameter") {
    return parameterIntent(
      text(element.dataset.parameter),
      text(element.dataset.value),
    );
  }
  if (kind === "recommendation") {
    return settingsIntent(jsonRecord(element.dataset.recommendation));
  }
  if (kind === "render_setup") {
    return settingsIntent(jsonRecord(element.dataset.renderSetup));
  }
  return {};
}

/** @param {PlaygroundIntent} intent */
export function playgroundIntentUrl(intent) {
  const query = new URLSearchParams();
  /** @type {Record<string, unknown>} */
  const intentValues = intent;
  for (const uid of intent.componentUids || []) query.append("component", uid);
  for (const uid of intent.revisionUids || []) query.append("revision", uid);
  set(query, "composition", intent.compositionUid);
  set(query, "prompt_composition", intent.promptCompositionUid);
  if (intent.promptScope)
    set(query, "prompt_scope", JSON.stringify(intent.promptScope));
  if (intent.promptCombination)
    set(query, "prompt_combination", JSON.stringify(intent.promptCombination));
  set(query, "image", intent.imageUid);
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
    componentUids: cleanValues(query.getAll("component")),
    revisionUids: cleanValues(query.getAll("revision")),
    compositionUid: text(query.get("composition")),
    imageUid: text(query.get("image")),
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

/** Own navigation from evidence to the Playground prefill surface. */
export class PlaygroundIntentNavigator {
  /** @param {{assign: (url: string) => void}} locationRef @param {{stagePromptCombination?: (selections: PromptCombinationSelection[]) => unknown, consumeUrl?: () => string}} [store] */
  constructor(locationRef, store = undefined) {
    this.locationRef = locationRef;
    this.store = store;
  }

  /** @param {HTMLElement} element */
  open(element) {
    this.openIntent(intentFromAnalyticsAction(element));
  }

  /** @param {PlaygroundIntent} intent */
  openIntent(intent) {
    if (
      Array.isArray(intent.promptCombination) &&
      this.store?.stagePromptCombination &&
      this.store.consumeUrl
    ) {
      this.store.stagePromptCombination(intent.promptCombination);
      this.locationRef.assign(this.store.consumeUrl());
      return;
    }
    this.locationRef.assign(playgroundIntentUrl(intent));
  }
}

/** Own source-specific removal from a consumed typed URL handoff. */
export class PlaygroundIntentUrlCleaner {
  /** @param {{href: string}} locationRef @param {{state: unknown, replaceState: (state: unknown, title: string, url?: string | URL | null) => void}} historyRef */
  constructor(locationRef, historyRef) {
    this.locationRef = locationRef;
    this.historyRef = historyRef;
  }

  /** @param {{type: string, imageUid?: string, compositionUid?: string, scope?: PromptScopeSource, selections?: PromptCombinationSelection[]}} source */
  removeTypedPromptSource(source) {
    const url = new URL(this.locationRef.href);
    let key = "";
    let matches = false;
    if (source.type === "image") {
      key = "prompt_image";
      matches = url.searchParams.get(key) === source.imageUid;
    } else if (source.type === "composition") {
      key = "prompt_composition";
      matches = url.searchParams.get(key) === source.compositionUid;
    } else if (source.type === "scope") {
      key = "prompt_scope";
      const currentScope = record(json(url.searchParams.get(key)));
      matches = sameScope(currentScope, source.scope);
    } else if (source.type === "combination") {
      key = "prompt_combination";
      matches = sameCombinationSelections(
        json(url.searchParams.get(key)),
        source.selections,
      );
    }
    if (!key || !matches) return false;
    url.searchParams.delete(key);
    const suffix = `${url.pathname}${url.search}${url.hash}`;
    this.historyRef.replaceState(this.historyRef.state, "", suffix);
    return true;
  }
}

/** Own one versioned, tab-local staging area for Analytics handoffs. */
export class PlaygroundIntentStore {
  /** @param {Storage} storage @param {string} [key] */
  constructor(storage, key = "comfyreview.playground-intent.v2") {
    this.storage = storage;
    this.key = key;
  }

  /** @returns {PlaygroundIntent} */
  read() {
    const stored = jsonRecord(this.storage.getItem(this.key));
    if (stored.version === 2) {
      return { ...record(stored.prompt), ...record(stored.render) };
    }
    return stored.version === 1 ? record(stored.intent) : {};
  }

  /** @param {PlaygroundIntent} incoming */
  merge(incoming) {
    const stored = this.#state();
    /** @type {PlaygroundIntent} */
    const prompt = { ...stored.prompt };
    /** @type {PlaygroundIntent} */
    const render = { ...stored.render };
    /** @type {Record<string, any>} */
    const incomingValues = incoming;
    /** @type {Record<string, any>} */
    const mergedValues = render;
    if (incoming.compositionUid) {
      prompt.compositionUid = incoming.compositionUid;
      prompt.componentUids = incoming.componentUids || [];
      delete prompt.revisionUids;
    } else if (incoming.componentUids?.length) {
      prompt.componentUids = cleanValues([
        ...(prompt.componentUids || []),
        ...incoming.componentUids,
      ]);
      delete prompt.compositionUid;
    }
    if (incoming.revisionUids?.length)
      prompt.revisionUids = incoming.revisionUids;
    if (incoming.promptImageUid || incoming.imageUid) {
      this.#setTypedPromptSource(
        prompt,
        "promptImageUid",
        incoming.promptImageUid || incoming.imageUid,
      );
      delete prompt.componentUids;
      delete prompt.revisionUids;
      delete prompt.compositionUid;
    }
    if (Array.isArray(incoming.loras)) prompt.loras = incoming.loras;
    for (const field of [
      "checkpoint",
      "sampler",
      "scheduler",
      "aspectFormat",
      "resolutionClass",
      "seedMode",
      "seed",
      "steps_min",
      "steps_max",
      "cfg_min",
      "cfg_max",
      "denoise",
    ]) {
      if (
        incomingValues[field] !== undefined &&
        incomingValues[field] !== null &&
        incomingValues[field] !== ""
      )
        mergedValues[field] = incomingValues[field];
    }
    if (incoming.renderImageUid || incoming.imageUid)
      render.renderImageUid = incoming.renderImageUid || incoming.imageUid;
    this.#write(prompt, render);
    return this.read();
  }

  /** @param {string} imageUid */
  stagePromptImage(imageUid) {
    const stored = this.#state();
    const prompt = { ...stored.prompt };
    this.#setTypedPromptSource(prompt, "promptImageUid", text(imageUid));
    this.#write(prompt, stored.render);
    return this.read();
  }

  /** @param {string} compositionUid */
  stagePromptComposition(compositionUid) {
    const stored = this.#state();
    const prompt = { ...stored.prompt };
    this.#setTypedPromptSource(
      prompt,
      "promptCompositionUid",
      text(compositionUid),
    );
    this.#write(prompt, stored.render);
    return this.read();
  }

  /** @param {PromptScopeSource} scope */
  stagePromptScope(scope) {
    const stored = this.#state();
    const prompt = { ...stored.prompt };
    this.#setTypedPromptSource(prompt, "promptScope", {
      kind: text(scope.kind),
      component_uid: text(scope.component_uid),
      revision_uid: text(scope.revision_uid) || null,
    });
    this.#write(prompt, stored.render);
    return this.read();
  }

  /** @param {PromptCombinationSelection[]} selections */
  stagePromptCombination(selections) {
    const stored = this.#state();
    const prompt = { ...stored.prompt };
    this.#setTypedPromptSource(
      prompt,
      "promptCombination",
      selections.map(combinationSelection),
    );
    this.#write(prompt, stored.render);
    return this.read();
  }

  /** @param {string} imageUid */
  stageRenderSetup(imageUid) {
    const stored = this.#state();
    this.#write(stored.prompt, {
      renderImageUid: text(imageUid),
    });
    return this.read();
  }

  clearPrompt() {
    const stored = this.#state();
    this.#write({}, stored.render);
  }

  /** @param {string} imageUid */
  clearPromptImage(imageUid) {
    const stored = this.#state();
    if (text(stored.prompt.promptImageUid) !== text(imageUid)) return;
    const prompt = { ...stored.prompt };
    delete prompt.promptImageUid;
    this.#write(prompt, stored.render);
  }

  /** @param {string} compositionUid */
  clearPromptComposition(compositionUid) {
    const stored = this.#state();
    if (text(stored.prompt.promptCompositionUid) !== text(compositionUid)) {
      return;
    }
    const prompt = { ...stored.prompt };
    delete prompt.promptCompositionUid;
    this.#write(prompt, stored.render);
  }

  /** @param {PromptScopeSource} scope */
  clearPromptScope(scope) {
    const stored = this.#state();
    const current = record(stored.prompt.promptScope);
    if (
      text(current.kind) !== text(scope.kind) ||
      text(current.component_uid) !== text(scope.component_uid) ||
      (text(current.revision_uid) || null) !==
        (text(scope.revision_uid) || null)
    ) {
      return;
    }
    const prompt = { ...stored.prompt };
    delete prompt.promptScope;
    this.#write(prompt, stored.render);
  }

  /** @param {PromptCombinationSelection[]} selections */
  clearPromptCombination(selections) {
    const stored = this.#state();
    if (
      !sameCombinationSelections(stored.prompt.promptCombination, selections)
    ) {
      return;
    }
    const prompt = { ...stored.prompt };
    delete prompt.promptCombination;
    this.#write(prompt, stored.render);
  }

  clearRender() {
    const stored = this.#state();
    this.#write(stored.prompt, {});
  }

  clear() {
    this.storage.removeItem(this.key);
  }

  /** Return the staged URL; the generator clears it after successful apply. */
  consumeUrl() {
    const intent = this.read();
    return playgroundIntentUrl(intent);
  }

  #state() {
    const stored = jsonRecord(this.storage.getItem(this.key));
    if (stored.version === 2) {
      return {
        prompt: record(stored.prompt),
        render: record(stored.render),
      };
    }
    if (stored.version === 1) {
      const legacy = record(stored.intent);
      return {
        prompt: {
          componentUids: legacy.componentUids,
          revisionUids: legacy.revisionUids,
          compositionUid: legacy.compositionUid,
          imageUid: legacy.imageUid,
        },
        render: legacy,
      };
    }
    return { prompt: {}, render: {} };
  }

  /** @param {Record<string, any>} prompt @param {Record<string, any>} render */
  #write(prompt, render) {
    this.storage.setItem(
      this.key,
      JSON.stringify({
        version: 2,
        prompt,
        render,
      }),
    );
  }

  /** @param {Record<string, any>} prompt @param {"promptImageUid" | "promptCompositionUid" | "promptScope" | "promptCombination"} key @param {unknown} value */
  #setTypedPromptSource(prompt, key, value) {
    delete prompt.promptImageUid;
    delete prompt.promptCompositionUid;
    delete prompt.promptScope;
    delete prompt.promptCombination;
    prompt[key] = value;
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

/** @param {unknown} selection @returns {PromptCombinationSelection} */
function combinationSelection(selection) {
  const item = record(selection);
  return {
    kind: text(item.kind),
    component_uid: text(item.component_uid),
    revision_uid: text(item.revision_uid) || null,
  };
}

/** @param {unknown} actual @param {unknown} expected */
function sameCombinationSelections(actual, expected) {
  if (!Array.isArray(actual) || !Array.isArray(expected)) return false;
  if (actual.length !== expected.length) return false;
  return actual.every((value, index) => {
    const left = combinationSelection(value);
    const right = combinationSelection(expected[index]);
    return (
      left.kind === right.kind &&
      left.component_uid === right.component_uid &&
      left.revision_uid === right.revision_uid
    );
  });
}

/** @param {Record<string, any>} actual @param {PromptScopeSource | undefined} expected */
function sameScope(actual, expected) {
  return Boolean(
    expected &&
    text(actual.kind) === text(expected.kind) &&
    text(actual.component_uid) === text(expected.component_uid) &&
    (text(actual.revision_uid) || null) ===
      (text(expected.revision_uid) || null),
  );
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

/** @param {unknown} value */
function values(value) {
  const normalized = text(value);
  return normalized ? [normalized] : [];
}

/** @param {unknown[]} value */
function cleanValues(value) {
  return value.map(text).filter(Boolean);
}

/** @param {unknown} value */
function jsonValues(value) {
  const parsed = json(value);
  return Array.isArray(parsed) ? cleanValues(parsed) : [];
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
