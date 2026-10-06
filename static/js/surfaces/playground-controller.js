import {
  combinationPromptPatch,
  compositionPromptState,
  imagePromptState,
  scopePromptPatch,
} from "../playground/generator-prompt-projector.js";

/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[], loras?: any[]) => void, applyState: (state: Record<string, any>) => string[] | void, applyIntent: (intent: Record<string, any>) => string[] | void, showResolvedComponents: (components: any[]) => void, value: () => {selections: any[], loras?: any[]}, dispose: () => void}} ModesBoundary */
/** @typedef {{render: (capabilities: any) => void, applyState: (state: Record<string, any>) => string[] | void, applyIntent: (intent: Record<string, any>) => string[] | void, stateValue: () => Record<string, any>, draftValue: () => any, renderSettings: () => any, renderGuidance: (payload: any, basis: "observed" | "predicted") => void, applyRenderSettings: (settings: Record<string, any>) => string[], applyParameter: (parameter: string, value: unknown) => boolean, value: () => any, useConcreteSeed: (seed: number) => void, setBusy: (busy: boolean) => void, dispose: () => void}} ControlsBoundary */
/** @typedef {{render: (draft: any, draftUid: string) => void, promptPayload: () => any, renderSnapshots: (payload: any) => void, renderEvidence: (payload: any) => void, generationPayload: (settings: any) => any, dispose: () => void}} DraftBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (payload: any) => void, renderLoading: (message?: string) => void, dispose: () => void}} GuidanceBoundary */
/** @typedef {{type: "image", imageUid: string} | {type: "composition", compositionUid: string} | {type: "scope", scope: {kind: string, component_uid: string, revision_uid: string | null}} | {type: "combination", selections: any}} TypedPromptSource */
/** @typedef {{api: ApiBoundary, modes: ModesBoundary, controls: ControlsBoundary, draft: DraftBoundary, guidance: GuidanceBoundary, requests: RequestBoundary, previewRequests: RequestBoundary & {cancelRequests: () => void}, guidanceRequests: RequestBoundary & {cancelRequests: () => void, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void}, stateRequests: RequestBoundary & {cancelRequests: () => void, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void}, prepareButton: HTMLButtonElement, submitButton: HTMLButtonElement, status: HTMLElement, result: HTMLElement, intent?: Record<string, any>, intentStore?: {clear?: () => void, clearPromptImage?: (imageUid: string) => void, clearPromptComposition?: (compositionUid: string) => void, clearPromptScope?: (scope: {kind: string, component_uid: string, revision_uid?: string | null}) => void, clearPromptCombination?: (selections: any) => void}, intentUrlCleaner?: {removeTypedPromptSource?: (source: TypedPromptSource) => boolean}}} PlaygroundDependencies */

/** Orchestrate catalog draft preparation and native generation submission. */
export class PlaygroundController {
  /** @param {PlaygroundDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.modes = dependencies.modes;
    this.controls = dependencies.controls;
    this.draft = dependencies.draft;
    this.guidance = dependencies.guidance;
    this.requests = dependencies.requests;
    this.previewRequests = dependencies.previewRequests;
    this.guidanceRequests = dependencies.guidanceRequests;
    this.stateRequests = dependencies.stateRequests;
    this.prepareButton = dependencies.prepareButton;
    this.submitButton = dependencies.submitButton;
    this.status = dependencies.status;
    this.result = dependencies.result;
    this.intent = dependencies.intent || {};
    this.typedPromptSource = null;
    this.intentStore = dependencies.intentStore || null;
    this.intentUrlCleaner = dependencies.intentUrlCleaner || null;
    this.draftReference = null;
    this.abortController = new AbortController();
    this.hasDraft = false;
    this.guidanceTimer = null;
    this.stateTimer = null;
    this.guidancePayload = null;
    /** @type {"observed" | "predicted"} */
    this.guidanceBasis = "observed";
  }

  /** Refresh the explanatory snapshot through the authoritative renderer. */
  async refreshPreview() {
    const payload = this.draft.promptPayload();
    if (!payload) return;
    this.previewRequests.cancelRequests();
    try {
      const rendered = await this.previewRequests.run((signal) =>
        this.api.post("playground/render-preview", payload, { signal }),
      );
      this.draft.renderSnapshots(rendered);
      await this.refreshEvidence();
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.status.textContent = errorMessage(error);
      }
    }
  }

  /** Refresh prompt- and sampler-oriented image evidence. */
  async refreshEvidence() {
    const prompt = this.draft.promptPayload();
    if (!prompt) return;
    const evidence = await this.api.post("playground/evidence", {
      ...this.controls.draftValue(),
      ...prompt,
    });
    this.draft.renderEvidence(evidence);
  }

  /** Load canonical catalog data and bind user actions. */
  async start() {
    try {
      this.typedPromptSource = resolveTypedPromptSource(this.intent);
    } catch (error) {
      this.status.textContent = `Prompt-Handoff abgewiesen: ${errorMessage(error)}`;
      this.prepareButton.disabled = true;
      this.submitButton.disabled = true;
      return;
    }
    this.prepareButton.addEventListener("click", () => void this.prepare(), {
      signal: this.abortController.signal,
    });
    this.submitButton.addEventListener("click", () => void this.submit(), {
      signal: this.abortController.signal,
    });
    try {
      const [catalog, capabilities, savedState] = await this.requests.run(
        (signal) =>
          Promise.all([
            this.api.get("playground/components", { signal }),
            this.api.get("playground/capabilities", { signal }),
            this.api
              .get("playground/generator-state", { signal })
              .catch(() => ({})),
          ]),
      );
      this.modes.render(
        catalog.components || [],
        capabilities.lora_definitions || [],
      );
      this.controls.render(capabilities);
      const rejected = [
        ...(this.modes.applyState(savedState) || []),
        ...(this.controls.applyState(savedState) || []),
        ...(await this.#applyIntent()),
      ];
      await this.refreshGuidance();
      this.status.textContent = rejected.length
        ? `Vorbelegung teilweise abgewiesen: ${rejected.join(", ")}`
        : hasPrefill(this.intent)
          ? "Vorbelegung übernommen – erstelle den Entwurf ausdrücklich"
          : "Bereit für deinen Entwurf";
      if (
        hasPrefill(this.intent) &&
        !rejected.length &&
        !hasTypedPromptSource(this.intent)
      )
        this.intentStore?.clear?.();
    } catch (error) {
      this.status.textContent = errorMessage(error);
      this.prepareButton.disabled = true;
    }
  }

  /** Refresh the shared server-side evidence for the current setup. */
  async refreshGuidance() {
    this.guidanceRequests.cancelRequests();
    this.guidance.renderLoading();
    try {
      const payload = await this.guidanceRequests.run((signal) =>
        this.api.post(
          "playground/render-guidance",
          this.controls.renderSettings(),
          { signal },
        ),
      );
      this.guidancePayload = payload;
      this.guidance.render(payload);
      this.controls.renderGuidance(payload, this.guidanceBasis);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.guidance.renderLoading(errorMessage(error));
      }
    }
  }

  /** @param {"observed" | "predicted"} basis */
  guidanceModeChanged(basis) {
    this.guidanceBasis = basis;
    if (this.guidancePayload)
      this.controls.renderGuidance(this.guidancePayload, basis);
  }

  /** Invalidate the draft and debounce a new evidence calculation. */
  settingsChanged() {
    this.invalidateDraft();
    this.#scheduleStateSave();
    this.guidanceRequests.cancel(this.guidanceTimer);
    this.guidanceTimer = this.guidanceRequests.schedule(
      () => void this.refreshGuidance(),
      180,
    );
  }

  /** @param {Record<string, any>} settings */
  applyGuidanceSetup(settings) {
    const rejected = this.controls.applyRenderSettings(settings);
    this.status.textContent = rejected.length
      ? `Nicht verfügbare Werte abgewiesen: ${rejected.join(", ")}`
      : "Empfohlenes Gesamtsetup übernommen";
  }

  /** @param {string} parameter @param {unknown} value */
  applyGuidanceParameter(parameter, value) {
    this.status.textContent = this.controls.applyParameter(parameter, value)
      ? `${parameterLabel(parameter)} übernommen`
      : `${parameterLabel(parameter)} ist in ComfyUI nicht verfügbar`;
  }

  /** Prepare a draft without mutating catalog revisions. */
  async prepare() {
    this.#setBusy(true);
    this.result.replaceChildren();
    this.status.textContent = "Prompt wird zusammengestellt …";
    try {
      const draft = await this.requests.run((signal) =>
        this.api.post(
          "playground/drafts",
          {
            ...(this.draftReference || this.modes.value()),
            generation: this.controls.draftValue(),
          },
          { signal },
        ),
      );
      this.controls.useConcreteSeed(Number(draft.seed));
      this.modes.showResolvedComponents(draft.components || []);
      this.draft.render(draft, String(draft.draft_uid));
      this.hasDraft = true;
      this.status.textContent = "Entwurf bereit zur Prüfung";
      await this.refreshEvidence();
    } catch (error) {
      this.hasDraft = false;
      this.status.textContent = errorMessage(error);
    } finally {
      this.#setBusy(false);
    }
  }

  /** Submit the reviewed snapshot through the native generation service. */
  async submit() {
    const payload = this.draft.generationPayload({
      ...this.controls.value(),
      loras: this.modes.value().loras || [],
    });
    if (!payload) return;
    this.#setBusy(true);
    this.status.textContent = "Generierung wird übergeben …";
    try {
      const submission = await this.requests.run((signal) =>
        this.api.post("generations", payload, { signal }),
      );
      /** @type {Array<Record<string, any>>} */
      const submissions = Array.isArray(submission.submissions)
        ? submission.submissions
        : [submission];
      this.result.dataset.state = "success";
      this.result.textContent = submissions
        .map((item) => `${item.generation_uid} · ${item.status}`)
        .join("\n");
      this.status.textContent =
        submissions.length === 1
          ? "An ComfyUI übergeben"
          : `${submissions.length} Generierungen an ComfyUI übergeben`;
    } catch (error) {
      this.result.dataset.state = "error";
      this.result.textContent = errorMessage(error);
      this.status.textContent = "Generierung fehlgeschlagen";
    } finally {
      this.#setBusy(false);
    }
  }

  /** Abort work and release all stateful collaborators. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.previewRequests.dispose();
    this.guidanceRequests.dispose();
    this.stateRequests.dispose();
    this.modes.dispose();
    this.controls.dispose();
    this.draft.dispose();
    this.guidance.dispose();
  }

  /** Use current mode controls after the user changes a prompt prefill. */
  clearDraftReference() {
    this.draftReference = null;
    this.invalidateDraft();
    this.#scheduleStateSave();
  }

  /** Invalidate a reviewed snapshot after its source settings change. */
  invalidateDraft() {
    this.hasDraft = false;
    this.submitButton.disabled = true;
  }

  /** @param {boolean} busy */
  #setBusy(busy) {
    this.prepareButton.disabled = busy;
    this.submitButton.disabled = busy || !this.hasDraft;
    this.controls.setBusy(busy);
  }

  #scheduleStateSave() {
    this.stateRequests.cancel(this.stateTimer);
    this.stateTimer = this.stateRequests.schedule(
      () => void this.#saveState(),
      180,
    );
  }

  async #saveState() {
    try {
      await this.#persistState();
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.status.textContent = `Einstellungen konnten nicht gespeichert werden: ${errorMessage(error)}`;
      }
    }
  }

  async #persistState() {
    this.stateRequests.cancelRequests();
    return this.stateRequests.run((signal) =>
      this.api.put(
        "playground/generator-state",
        {
          ...this.modes.value(),
          ...this.controls.stateValue(),
        },
        { signal },
      ),
    );
  }

  async #applyIntent() {
    let intent = this.intent;
    const typedSource = this.typedPromptSource;
    const legacyImageUid = String(intent.imageUid || "");
    const renderImageUid = String(intent.renderImageUid || legacyImageUid);
    let promptHandoff = null;
    if (typedSource?.type === "image") {
      promptHandoff = await this.#loadHandoff(typedSource.imageUid);
    } else if (legacyImageUid) {
      promptHandoff = await this.#loadHandoff(legacyImageUid);
    }
    let renderHandoff = null;
    if (renderImageUid) {
      renderHandoff =
        promptHandoff &&
        renderImageUid ===
          (typedSource?.type === "image"
            ? typedSource.imageUid
            : legacyImageUid)
          ? promptHandoff
          : await this.#loadHandoff(renderImageUid);
    }

    /** @type {string[]} */
    const rejected = [];
    if (typedSource) {
      if (renderHandoff) {
        intent = { ...intent, ...renderIntent(renderHandoff) };
      }
      this.intent = intent;
      rejected.push(...(this.controls.applyIntent(intent) || []));
      this.draftReference = null;
      rejected.push(
        ...(await this.#applyTypedPromptSource(typedSource, promptHandoff)),
      );
      return rejected;
    }
    if (legacyImageUid)
      intent = { ...intent, ...promptIntent(promptHandoff || {}) };
    if (renderHandoff) {
      intent = { ...intent, ...renderIntent(renderHandoff) };
    }

    this.intent = intent;
    rejected.push(...(this.modes.applyIntent(intent) || []));
    rejected.push(...(this.controls.applyIntent(intent) || []));
    if (Array.isArray(intent.revisionUids) && intent.revisionUids.length) {
      this.draftReference = { revision_uids: intent.revisionUids };
    } else if (intent.compositionUid) {
      this.draftReference = { composition_uid: intent.compositionUid };
    }
    return rejected;
  }

  /** @param {TypedPromptSource} source @param {any} imageHandoff @returns {Promise<string[]>} */
  async #applyTypedPromptSource(source, imageHandoff) {
    const priorPromptState = this.modes.value();
    let applyAttempted = false;
    const label = promptSourceLabel(source.type);
    try {
      const promptState = await this.#typedPromptState(source, imageHandoff);
      applyAttempted = true;
      const promptRejections = this.modes.applyState(promptState) || [];
      if (promptRejections.length) {
        return [
          `${label} abgewiesen: ${promptRejections.join(", ")}`,
          ...this.#restorePromptState(priorPromptState),
        ];
      }
      this.stateRequests.cancel(this.stateTimer);
      this.stateTimer = null;
      await this.#persistState();
    } catch (error) {
      return [
        `${label} konnte nicht übernommen werden: ${errorMessage(error)}`,
        ...(applyAttempted ? this.#restorePromptState(priorPromptState) : []),
      ];
    }
    try {
      this.#clearTypedPromptSource(source);
    } catch (error) {
      return [
        `${label} übernommen, Quelle konnte nicht entfernt werden: ${errorMessage(error)}`,
      ];
    }
    return [];
  }

  /** @param {TypedPromptSource} source @param {any} imageHandoff */
  async #typedPromptState(source, imageHandoff) {
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

  /** @param {TypedPromptSource} source */
  #clearTypedPromptSource(source) {
    if (source.type === "image") {
      this.intentStore?.clearPromptImage?.(source.imageUid);
    } else if (source.type === "composition") {
      this.intentStore?.clearPromptComposition?.(source.compositionUid);
    } else if (source.type === "combination") {
      this.intentStore?.clearPromptCombination?.(source.selections);
    } else {
      this.intentStore?.clearPromptScope?.(source.scope);
    }
    this.intentUrlCleaner?.removeTypedPromptSource?.(source);
  }

  /** @param {Record<string, any>} state @returns {string[]} */
  #restorePromptState(state) {
    try {
      const rejected = this.modes.applyState(state) || [];
      return rejected.length
        ? [
            `Vorheriger Prompt-State konnte nicht vollständig wiederhergestellt werden: ${rejected.join(", ")}`,
          ]
        : [];
    } catch (error) {
      return [
        `Vorheriger Prompt-State konnte nicht wiederhergestellt werden: ${errorMessage(error)}`,
      ];
    }
  }

  /** @param {string} imageUid */
  #loadHandoff(imageUid) {
    return this.requests.run((signal) =>
      this.api.get(`images/${encodeURIComponent(imageUid)}/generator-handoff`, {
        signal,
      }),
    );
  }
}

class AmbiguousTypedPromptSourceError extends Error {}

/** @param {Record<string, any>} intent @returns {TypedPromptSource | null} */
function resolveTypedPromptSource(intent) {
  /** @type {TypedPromptSource[]} */
  const sources = [];
  const imageUid = String(intent.promptImageUid || "").trim();
  if (imageUid) sources.push({ type: "image", imageUid });
  const compositionUid = String(intent.promptCompositionUid || "").trim();
  if (compositionUid) sources.push({ type: "composition", compositionUid });
  const scope = intent.promptScope;
  if (scope && typeof scope === "object") {
    sources.push({
      type: "scope",
      scope: {
        kind: String(scope.kind).trim(),
        component_uid: String(scope.component_uid).trim(),
        revision_uid: String(scope.revision_uid || "").trim() || null,
      },
    });
  }
  if (
    intent.promptCombination !== undefined &&
    intent.promptCombination !== null
  ) {
    sources.push({
      type: "combination",
      selections: intent.promptCombination,
    });
  }
  if (sources.length > 1) {
    throw new AmbiguousTypedPromptSourceError(
      "Mehrdeutiger Prompt-Handoff: Bitte nur eine Quelle (Bild, Composition, Scope oder Combination) auswählen.",
    );
  }
  return sources[0] || null;
}

/** @param {Record<string, any>} intent */
function hasTypedPromptSource(intent) {
  return resolveTypedPromptSource(intent) !== null;
}

/** @param {string} type */
function promptSourceLabel(type) {
  if (type === "image") return "Image-Prompt";
  if (type === "composition") return "Composition-Prompt";
  if (type === "combination") return "Combination-Prompt";
  return "Scope-Prompt";
}

/** @param {Record<string, any>} handoff */
function promptIntent(handoff) {
  const prompt = handoff.prompt_setup || {};
  return {
    componentUids: Array.isArray(prompt.component_uids)
      ? prompt.component_uids
      : [],
    loras: Array.isArray(prompt.loras) ? prompt.loras : [],
  };
}

/** @param {Record<string, any>} handoff */
function renderIntent(handoff) {
  const render = handoff.render_setup || {};
  const stages = Array.isArray(render.sampler_stages)
    ? render.sampler_stages
    : [];
  const stage = stages[0] || {};
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

/** @param {Record<string, any>} intent */
function hasPrefill(intent) {
  return Object.values(intent).some((value) =>
    Array.isArray(value) ? value.length > 0 : value !== "" && value != null,
  );
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}

/** @param {string} parameter */
function parameterLabel(parameter) {
  return (
    {
      checkpoint: "Checkpoint",
      sampler: "Sampler",
      scheduler: "Scheduler",
      steps: "Steps",
      cfg: "CFG",
      denoise: "Denoise",
    }[parameter] || parameter
  );
}
