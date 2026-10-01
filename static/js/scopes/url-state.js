/**
 * @typedef {Object} ScopeUrlState
 * @property {string[]} scopes
 * @property {"all" | "classified" | "unclassified"} classification
 * @property {string} model
 * @property {string} checkpoint
 * @property {string} setKey
 * @property {"top" | "worst"} mode
 * @property {number} offset
 */

/** @param {string} search @returns {ScopeUrlState} */
export function readScopeUrlState(search) {
  const parameters = new URLSearchParams(search);
  const classification = parameters.get("classification");
  const mode = parameters.get("mode");
  const rawOffset = Number.parseInt(parameters.get("offset") || "0", 10);
  return {
    scopes: normalizeScopes(parameters.getAll("scope")),
    classification:
      classification === "classified" || classification === "unclassified"
        ? classification
        : "all",
    model: parameters.get("model")?.trim() || "",
    checkpoint: parameters.get("checkpoint")?.trim() || "",
    setKey: parameters.get("set_key")?.trim() || "",
    mode: mode === "worst" ? "worst" : "top",
    offset: Number.isSafeInteger(rawOffset) && rawOffset > 0 ? rawOffset : 0,
  };
}

/** @param {ScopeUrlState} state @returns {string} */
export function writeScopeUrlState(state) {
  const parameters = new URLSearchParams();
  for (const scope of normalizeScopes(state.scopes)) {
    parameters.append("scope", scope);
  }
  if (state.classification !== "all") {
    parameters.set("classification", state.classification);
  }
  setWhenPresent(parameters, "model", state.model);
  setWhenPresent(parameters, "checkpoint", state.checkpoint);
  setWhenPresent(parameters, "set_key", state.setKey);
  if (state.mode === "worst") {
    parameters.set("mode", "worst");
  }
  if (state.offset > 0) {
    parameters.set("offset", String(state.offset));
  }
  const query = parameters.toString();
  return query ? `?${query}` : "";
}

/** @param {string[]} scopes @returns {string[]} */
export function normalizeScopes(scopes) {
  return [
    ...new Set(scopes.map((scope) => String(scope).trim()).filter(Boolean)),
  ].sort();
}

/** @param {URLSearchParams} parameters @param {string} key @param {string} value */
function setWhenPresent(parameters, key, value) {
  const normalized = String(value || "").trim();
  if (normalized) {
    parameters.set(key, normalized);
  }
}
