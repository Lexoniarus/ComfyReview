import {
  combinationPromptPatch,
  compositionPromptState,
  imagePromptState,
  scopePromptPatch,
} from "./generator-prompt-projector.js";

/** Own loading, atomic application, persistence and cleanup of one handoff. */
export class GeneratorHandoffApplier {
  /** @param {{api: {get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>}, modes: {value: () => Record<string, any>, applyState: (state: Record<string, any>) => string[] | void}, controls: {stateValue: () => Record<string, any>, applyState: (state: Record<string, any>) => string[] | void, applyIntent: (intent: Record<string, any>) => string[] | void}, persistence: {save: () => Promise<any>}, urlCleaner: {removeHandoff: () => boolean}, requests: {run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>}}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.modes = dependencies.modes;
    this.controls = dependencies.controls;
    this.persistence = dependencies.persistence;
    this.urlCleaner = dependencies.urlCleaner;
    this.requests = dependencies.requests;
  }

  /** @param {Record<string, any>} intent */
  async apply(intent) {
    if (!hasHandoff(intent)) return { applied: false, rejected: [] };
    const previousPrompt = this.modes.value();
    const previousControls = this.controls.stateValue();
    try {
      const typedSource = resolveTypedPromptSource(intent);
      const promptHandoff =
        typedSource?.type === "image"
          ? await this.#loadImage(typedSource.imageUid)
          : null;
      const renderImageUid = String(intent.renderImageUid || "");
      const renderHandoff = renderImageUid
        ? promptHandoff &&
          typedSource?.type === "image" &&
          typedSource.imageUid === renderImageUid
          ? promptHandoff
          : await this.#loadImage(renderImageUid)
        : null;
      if (renderHandoff && !renderHandoff.render_setup?.applicable) {
        const issues = Array.isArray(renderHandoff.render_setup?.issues)
          ? renderHandoff.render_setup.issues.join(", ")
          : "nicht anwendbar";
        throw new Error(
          `Generierungseinstellungen können nicht übernommen werden: ${issues}`,
        );
      }
      const projectedIntent = renderHandoff
        ? { ...intent, ...renderIntent(renderHandoff) }
        : intent;
      const rejected = [...(this.controls.applyIntent(projectedIntent) || [])];
      if (typedSource) {
        const promptState = await this.#promptState(typedSource, promptHandoff);
        rejected.push(...(this.modes.applyState(promptState) || []));
      }
      if (rejected.length) {
        throw new HandoffRejectedError(rejected);
      }
      await this.persistence.save();
      try {
        this.urlCleaner.removeHandoff();
      } catch (error) {
        return {
          applied: true,
          rejected: [
            `URL konnte nicht bereinigt werden: ${errorMessage(error)}`,
          ],
        };
      }
      return { applied: true, rejected: [] };
    } catch (error) {
      const restoreIssues = [];
      try {
        restoreIssues.push(...(this.modes.applyState(previousPrompt) || []));
      } catch (restoreError) {
        restoreIssues.push(errorMessage(restoreError));
      }
      try {
        restoreIssues.push(
          ...(this.controls.applyState(previousControls) || []),
        );
      } catch (restoreError) {
        restoreIssues.push(errorMessage(restoreError));
      }
      const rejected =
        error instanceof HandoffRejectedError
          ? error.rejected
          : [errorMessage(error)];
      return {
        applied: false,
        rejected: [
          ...rejected,
          ...restoreIssues.map((item) => `Rollback: ${item}`),
        ],
      };
    }
  }

  /** @param {TypedPromptSource} source @param {any} imageHandoff */
  async #promptState(source, imageHandoff) {
    if (source.type === "image") {
      return imagePromptState(imageHandoff?.prompt_setup || {});
    }
    if (source.type === "composition") {
      const handoff = await this.requests.run((signal) =>
        this.api.get(
          `playground/compositions/${encodeURIComponent(source.compositionUid)}/prompt-selections`,
          { signal },
        ),
      );
      return compositionPromptState(handoff.selections);
    }
    if (source.type === "combination") {
      return combinationPromptPatch(source.selections);
    }
    return scopePromptPatch(source.scope);
  }

  /** @param {string} imageUid */
  #loadImage(imageUid) {
    return this.requests.run((signal) =>
      this.api.get(`images/${encodeURIComponent(imageUid)}/generator-handoff`, {
        signal,
      }),
    );
  }
}

class HandoffRejectedError extends Error {
  /** @param {string[]} rejected */
  constructor(rejected) {
    super(rejected.join(", "));
    this.rejected = rejected;
  }
}

/** @typedef {{type: "image", imageUid: string} | {type: "composition", compositionUid: string} | {type: "scope", scope: {kind: string, component_uid: string, revision_uid: string | null}} | {type: "combination", selections: any}} TypedPromptSource */

/** @param {Record<string, any>} intent @returns {TypedPromptSource | null} */
function resolveTypedPromptSource(intent) {
  /** @type {TypedPromptSource[]} */
  const sources = [];
  const imageUid = String(intent.promptImageUid || "").trim();
  if (imageUid) sources.push({ type: "image", imageUid });
  const compositionUid = String(intent.promptCompositionUid || "").trim();
  if (compositionUid) sources.push({ type: "composition", compositionUid });
  if (intent.promptScope && typeof intent.promptScope === "object") {
    sources.push({
      type: "scope",
      scope: {
        kind: String(intent.promptScope.kind || "").trim(),
        component_uid: String(intent.promptScope.component_uid || "").trim(),
        revision_uid:
          String(intent.promptScope.revision_uid || "").trim() || null,
      },
    });
  }
  if (intent.promptCombination != null) {
    sources.push({ type: "combination", selections: intent.promptCombination });
  }
  if (sources.length > 1) {
    throw new Error(
      "Mehrdeutiger Prompt-Handoff: Bitte nur eine Prompt-Quelle verwenden.",
    );
  }
  return sources[0] || null;
}

/** @param {Record<string, any>} intent */
function hasHandoff(intent) {
  return Object.values(intent).some((value) =>
    Array.isArray(value) ? value.length > 0 : value !== "" && value != null,
  );
}

/** @param {Record<string, any>} handoff */
function renderIntent(handoff) {
  const render = handoff.render_setup || {};
  const stage = Array.isArray(render.sampler_stages)
    ? render.sampler_stages[0] || {}
    : {};
  return {
    checkpoint: render.checkpoint,
    sampler: stage.sampler,
    scheduler: stage.scheduler,
    seedMode: "fixed",
    seed: render.seed,
    steps_min: stage.steps,
    steps_max: stage.steps,
    cfg_min: stage.cfg,
    cfg_max: stage.cfg,
    denoise: stage.denoise,
    aspectFormat: render.aspect_format,
    resolutionClass: render.resolution_class,
  };
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Übergabe ist fehlgeschlagen.";
}
