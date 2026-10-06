const numericFields = [
  "seed",
  "steps_min",
  "steps_max",
  "cfg_min",
  "cfg_max",
  "denoise",
];

/** @typedef {{componentUids?: string[], revisionUids?: string[], compositionUid?: string, imageUid?: string, promptImageUid?: string, renderImageUid?: string, loras?: any[], checkpoint?: string, sampler?: string, scheduler?: string, aspectFormat?: string, resolutionClass?: string, seedMode?: string, seed?: number, steps_min?: number, steps_max?: number, cfg_min?: number, cfg_max?: number, denoise?: number}} PlaygroundIntent */

/** @param {HTMLElement} element @returns {PlaygroundIntent} */
export function intentFromAnalyticsAction(element) {
  const kind = String(element.dataset.playgroundIntent || "");
  if (kind === "scope") {
    return {
      componentUids: [
        ...values(element.dataset.componentUid),
        ...jsonValues(element.dataset.componentUids),
      ],
    };
  }
  if (kind === "composition") {
    return {
      compositionUid: text(element.dataset.compositionUid),
      componentUids: jsonValues(element.dataset.componentUids),
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
  /** @param {{assign: (url: string) => void}} locationRef */
  constructor(locationRef) {
    this.locationRef = locationRef;
  }

  /** @param {HTMLElement} element */
  open(element) {
    this.locationRef.assign(
      playgroundIntentUrl(intentFromAnalyticsAction(element)),
    );
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

  /** @param {string} componentUid @param {string} kind */
  mergePromptComponent(componentUid, kind) {
    const stored = this.#state();
    const current = stored.prompt;
    const kinds = stored.promptKinds;
    const previous = text(kinds[kind]);
    const values = (current.componentUids || []).filter(
      (/** @type {string} */ uid) => uid !== previous && uid !== componentUid,
    );
    values.push(componentUid);
    current.componentUids = values;
    delete current.compositionUid;
    kinds[kind] = componentUid;
    this.#write(current, stored.render, kinds);
    return this.read();
  }

  /** @param {PlaygroundIntent} incoming */
  merge(incoming) {
    const stored = this.#state();
    /** @type {PlaygroundIntent} */
    const prompt = { ...stored.prompt };
    /** @type {PlaygroundIntent} */
    const render = { ...stored.render };
    const promptKinds = stored.promptKinds;
    /** @type {Record<string, any>} */
    const incomingValues = incoming;
    /** @type {Record<string, any>} */
    const mergedValues = render;
    if (incoming.compositionUid) {
      prompt.compositionUid = incoming.compositionUid;
      prompt.componentUids = incoming.componentUids || [];
      delete prompt.revisionUids;
      for (const key of Object.keys(promptKinds)) delete promptKinds[key];
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
      prompt.promptImageUid = incoming.promptImageUid || incoming.imageUid;
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
    this.#write(prompt, render, promptKinds);
    return this.read();
  }

  /** @param {Record<string, any>} promptSetup */
  stagePromptSetup(promptSetup) {
    const stored = this.#state();
    const setup = record(promptSetup);
    this.#write(
      {
        componentUids: cleanValues(
          Array.isArray(setup.component_uids) ? setup.component_uids : [],
        ),
        loras: Array.isArray(setup.loras) ? setup.loras : [],
      },
      stored.render,
      {},
    );
    return this.read();
  }

  /** @param {string} imageUid */
  stagePromptImage(imageUid) {
    const stored = this.#state();
    this.#write({ promptImageUid: text(imageUid) }, stored.render, {});
    return this.read();
  }

  /** @param {string} imageUid */
  stageRenderSetup(imageUid) {
    const stored = this.#state();
    this.#write(
      stored.prompt,
      { renderImageUid: text(imageUid) },
      stored.promptKinds,
    );
    return this.read();
  }

  clearPrompt() {
    const stored = this.#state();
    this.#write({}, stored.render, {});
  }

  /** @param {string} imageUid */
  clearPromptImage(imageUid) {
    const stored = this.#state();
    if (text(stored.prompt.promptImageUid) !== text(imageUid)) return;
    const prompt = { ...stored.prompt };
    delete prompt.promptImageUid;
    this.#write(prompt, stored.render, stored.promptKinds);
  }

  clearRender() {
    const stored = this.#state();
    this.#write(stored.prompt, {}, stored.promptKinds);
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
        promptKinds: record(stored.prompt_kinds),
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
        promptKinds: record(stored.prompt_kinds),
      };
    }
    return { prompt: {}, render: {}, promptKinds: {} };
  }

  /** @param {Record<string, any>} prompt @param {Record<string, any>} render @param {Record<string, string>} promptKinds */
  #write(prompt, render, promptKinds) {
    this.storage.setItem(
      this.key,
      JSON.stringify({
        version: 2,
        prompt,
        render,
        prompt_kinds: promptKinds,
      }),
    );
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
