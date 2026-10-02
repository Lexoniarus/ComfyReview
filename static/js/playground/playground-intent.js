const numericFields = [
  "seed",
  "steps_min",
  "steps_max",
  "cfg_min",
  "cfg_max",
  "denoise",
];

/** @typedef {{componentUids?: string[], revisionUids?: string[], compositionUid?: string, imageUid?: string, generationProfileUid?: string, checkpoint?: string, sampler?: string, scheduler?: string, seedMode?: string, seed?: number, steps_min?: number, steps_max?: number, cfg_min?: number, cfg_max?: number, denoise?: number}} PlaygroundIntent */

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
  set(query, "profile", intent.generationProfileUid);
  set(query, "checkpoint", intent.checkpoint);
  set(query, "sampler", intent.sampler);
  set(query, "scheduler", intent.scheduler);
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
    generationProfileUid: text(query.get("profile")),
    checkpoint: text(query.get("checkpoint")),
    sampler: text(query.get("sampler")),
    scheduler: text(query.get("scheduler")),
    seedMode: text(query.get("seed_mode")),
  };
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

/** @param {string} parameter @param {string} value */
function parameterIntent(parameter, value) {
  if (["checkpoint", "sampler", "scheduler"].includes(parameter)) {
    return { [parameter]: value };
  }
  const number = Number(value);
  if (!Number.isFinite(number)) return {};
  if (parameter === "steps") return { steps_min: number, steps_max: number };
  if (parameter === "cfg") return { cfg_min: number, cfg_max: number };
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
