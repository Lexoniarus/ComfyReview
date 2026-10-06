/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[], loras?: any[]) => void, applyState: (state: Record<string, any>) => string[] | void, showResolvedComponents: (components: any[]) => void, value: () => {selections: any[], loras?: any[]}, setBusy: (busy: boolean) => void, dispose: () => void}} ModesBoundary */
/** @typedef {{render: (capabilities: any) => void, applyState: (state: Record<string, any>) => string[] | void, applyIntent: (intent: Record<string, any>) => string[] | void, stateValue: () => Record<string, any>, draftValue: () => any, renderSettings: () => any, renderGuidance: (payload: any, basis: "observed" | "predicted") => void, applyRenderSettings: (settings: Record<string, any>) => string[], applyParameter: (parameter: string, value: unknown) => boolean, value: () => any, useConcreteSeed: (seed: number) => void, setBusy: (busy: boolean) => void, dispose: () => void}} ControlsBoundary */
/** @typedef {{render: (draft: any, draftUid: string) => void, clear: () => void, promptPayload: () => any, renderSnapshots: (payload: any) => void, renderEvidence: (payload: any) => void, generationPayload: (settings: any) => any, dispose: () => void}} DraftBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (payload: any) => void, renderLoading: (message?: string) => void, dispose: () => void}} GuidanceBoundary */
/** @typedef {{api: ApiBoundary, modes: ModesBoundary, controls: ControlsBoundary, draft: DraftBoundary, guidance: GuidanceBoundary, requests: RequestBoundary, previewRequests: RequestBoundary & {cancelRequests: () => void}, guidanceRequests: RequestBoundary & {cancelRequests: () => void, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void}, persistence: {load: () => Promise<any>, schedule: () => void, flush: () => Promise<any>, dispose: () => void}, handoffApplier: {apply: (intent: Record<string, any>) => Promise<{applied: boolean, rejected: string[]}>}, draftSession: {isReady: boolean, invalidate: () => void, prepare: (operation: (signal: AbortSignal) => Promise<Record<string, any>>) => Promise<Record<string, any>>, submit: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}, prepareButton: HTMLButtonElement, submitButton: HTMLButtonElement, status: HTMLElement, result: HTMLElement, intent?: Record<string, any>}} PlaygroundDependencies */

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
    this.persistence = dependencies.persistence;
    this.handoffApplier = dependencies.handoffApplier;
    this.draftSession = dependencies.draftSession;
    this.prepareButton = dependencies.prepareButton;
    this.submitButton = dependencies.submitButton;
    this.status = dependencies.status;
    this.result = dependencies.result;
    this.intent = dependencies.intent || {};
    this.abortController = new AbortController();
    this.guidanceTimer = null;
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
    try {
      const evidence = await this.previewRequests.run((signal) =>
        this.api.post(
          "playground/evidence",
          {
            ...this.controls.draftValue(),
            ...prompt,
          },
          { signal },
        ),
      );
      this.draft.renderEvidence(evidence);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.status.textContent = errorMessage(error);
      }
    }
  }

  /** Load canonical catalog data and bind user actions. */
  async start() {
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
            this.persistence.load().catch(() => ({})),
          ]),
      );
      this.modes.render(
        catalog.components || [],
        capabilities.lora_definitions || [],
      );
      this.controls.render(capabilities);
      const stateRejected = [
        ...(this.modes.applyState(savedState) || []),
        ...(this.controls.applyState(savedState) || []),
      ];
      const handoff = await this.handoffApplier.apply(this.intent);
      const rejected = [...stateRejected, ...handoff.rejected];
      await this.refreshGuidance();
      this.status.textContent = rejected.length
        ? `Vorbelegung teilweise abgewiesen: ${rejected.join(", ")}`
        : handoff.applied
          ? "Vorbelegung übernommen – erstelle den Entwurf ausdrücklich"
          : "Bereit für deinen Entwurf";
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
    this.status.textContent = "Änderungen erkannt – Entwurf neu erstellen";
    this.persistence.schedule();
    this.guidanceRequests.cancel(this.guidanceTimer);
    this.guidanceTimer = this.guidanceRequests.schedule(
      () => void this.refreshGuidance(),
      180,
    );
  }

  /** @param {Record<string, any>} settings */
  applyGuidanceSetup(settings) {
    const rejected = this.controls.applyRenderSettings(settings);
    if (!rejected.length) this.settingsChanged();
    this.status.textContent = rejected.length
      ? `Nicht verfügbare Werte abgewiesen: ${rejected.join(", ")}`
      : "Empfohlenes Gesamtsetup übernommen";
  }

  /** @param {string} parameter @param {unknown} value */
  applyGuidanceParameter(parameter, value) {
    const applied = this.controls.applyParameter(parameter, value);
    if (applied) this.settingsChanged();
    this.status.textContent = applied
      ? `${parameterLabel(parameter)} übernommen`
      : `${parameterLabel(parameter)} ist in ComfyUI nicht verfügbar`;
  }

  /** Prepare a draft without mutating catalog revisions. */
  async prepare() {
    this.invalidateDraft();
    this.#setBusy(true);
    this.status.textContent = "Prompt wird zusammengestellt …";
    try {
      const draft = await this.draftSession.prepare((signal) =>
        this.api.post(
          "playground/drafts",
          {
            ...this.modes.value(),
            generation: this.controls.draftValue(),
          },
          { signal },
        ),
      );
      this.controls.useConcreteSeed(Number(draft.seed));
      this.modes.showResolvedComponents(draft.components || []);
      this.draft.render(draft, String(draft.draft_uid));
      this.status.textContent = "Entwurf bereit zur Prüfung";
      await this.refreshEvidence();
    } catch (error) {
      this.draft.clear();
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.status.textContent = errorMessage(error);
      }
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
      const submission = await this.draftSession.submit((signal) =>
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
      if (error instanceof DOMException && error.name === "AbortError") return;
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
    this.draftSession.dispose();
    this.persistence.dispose();
    this.modes.dispose();
    this.controls.dispose();
    this.draft.dispose();
    this.guidance.dispose();
  }

  /** Persist prompt controls after the user changes them. */
  promptSettingsChanged() {
    this.invalidateDraft();
    this.status.textContent = "Änderungen erkannt – Entwurf neu erstellen";
    this.persistence.schedule();
  }

  /** Invalidate a reviewed snapshot after its source settings change. */
  invalidateDraft() {
    this.draftSession.invalidate();
    this.previewRequests.cancelRequests();
    this.draft.clear();
    this.result.replaceChildren();
    delete this.result.dataset.state;
    this.submitButton.disabled = true;
  }

  /** @param {boolean} busy */
  #setBusy(busy) {
    this.prepareButton.disabled = busy;
    this.submitButton.disabled = busy || !this.draftSession.isReady;
    this.modes.setBusy(busy);
    this.controls.setBusy(busy);
  }
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
