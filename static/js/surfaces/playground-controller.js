import {
  variantGenerationPayload,
  variantWithReviewedPayload,
} from "../playground/variant-inspector.js";

/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[], loras?: any[]) => void, applyState: (state: Record<string, any>) => string[] | void, value: () => {selections: any[], loras?: any[], component_overrides?: any[]}, stateValue: () => {selections: any[], loras: any[]}, setBusy: (busy: boolean) => void, dispose: () => void}} ModesBoundary */
/** @typedef {{render: (capabilities: any) => void, applyState: (state: Record<string, any>) => string[] | void, stateValue: () => Record<string, any>, variantValue: () => {variant_count: number, generation: Record<string, any>}, renderSettings: () => any, renderGuidance: (payload: any, basis: "observed" | "predicted") => void, applyRenderSettings: (settings: Record<string, any>) => string[], applyParameter: (parameter: string, value: unknown) => boolean, setBusy: (busy: boolean) => void, dispose: () => void}} ControlsBoundary */
/** @typedef {{render: (variant: any) => void, clear: () => void, promptPayload: () => any, renderSnapshots: (payload: any) => void, renderEvidence: (payload: any) => void, generationPayload: () => any, dispose: () => void}} InspectorBoundary */
/** @typedef {{snapshot: () => any, activeVariant: () => any, selectedVariants: () => any[], inspected?: string, inspect: (uid: string) => boolean, select: (uid: string, selected: boolean) => boolean, review: (uid: string, payload: Record<string, any>) => boolean, reviewedPayload: (uid: string) => Record<string, any> | null, markStale: () => void, prepare: (operation: (signal: AbortSignal) => Promise<Record<string, any>>) => Promise<Record<string, any>>, submit: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, readonly hasVariants: boolean, readonly canSubmit: boolean, dispose: () => void}} VariantSessionBoundary */
/** @typedef {{render: (state: any) => void, dispose: () => void}} BoardBoundary */
/** @typedef {{setVariantsAvailable: (available: boolean) => void, show: (step: string) => boolean, openInspector: () => void, dispose: () => void}} WorkspaceBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests?: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (payload: any) => void, renderLoading: (message?: string) => void, dispose: () => void}} GuidanceBoundary */
/** @typedef {{api: ApiBoundary, modes: ModesBoundary, controls: ControlsBoundary, inspector: InspectorBoundary, board: BoardBoundary, workspace: WorkspaceBoundary, session: VariantSessionBoundary, guidance: GuidanceBoundary, requests: RequestBoundary, previewRequests: RequestBoundary & {cancelRequests: () => void}, guidanceRequests: RequestBoundary & {cancelRequests: () => void, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void}, persistence: {load: () => Promise<any>, schedule: () => void, flush: () => Promise<any>, dispose: () => void}, handoffApplier: {apply: (intent: Record<string, any>) => Promise<{applied: boolean, rejected: string[], promptSourceImageUid: string | null}>}, prepareButton: HTMLButtonElement, refreshButton: HTMLButtonElement, submitButton: HTMLButtonElement, status: HTMLElement, result: HTMLElement, variantSummary: HTMLElement, selectedCount: HTMLElement, intent?: Record<string, any>}} PlaygroundDependencies */

/** Orchestrate setup, transient variant review and exact batch submission. */
export class PlaygroundController {
  /** @param {PlaygroundDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.modes = dependencies.modes;
    this.controls = dependencies.controls;
    this.inspector = dependencies.inspector;
    this.board = dependencies.board;
    this.workspace = dependencies.workspace;
    this.session = dependencies.session;
    this.guidance = dependencies.guidance;
    this.requests = dependencies.requests;
    this.previewRequests = dependencies.previewRequests;
    this.guidanceRequests = dependencies.guidanceRequests;
    this.persistence = dependencies.persistence;
    this.handoffApplier = dependencies.handoffApplier;
    this.prepareButton = dependencies.prepareButton;
    this.refreshButton = dependencies.refreshButton;
    this.submitButton = dependencies.submitButton;
    this.status = dependencies.status;
    this.result = dependencies.result;
    this.variantSummary = dependencies.variantSummary;
    this.selectedCount = dependencies.selectedCount;
    this.intent = dependencies.intent || {};
    this.abortController = new AbortController();
    this.guidanceTimer = null;
    this.guidancePayload = null;
    this.promptSourceImageUid = null;
    this.imagePromptEdited = false;
    this.inspectedDraftUid = "";
    /** @type {"observed" | "predicted"} */
    this.guidanceBasis = "observed";
  }

  /** Load canonical catalog data and bind owned user actions. */
  async start() {
    for (const button of [this.prepareButton, this.refreshButton]) {
      button.addEventListener("click", () => void this.prepare(), {
        signal: this.abortController.signal,
      });
    }
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
      this.promptSourceImageUid = handoff.promptSourceImageUid;
      this.imagePromptEdited = false;
      const rejected = [...stateRejected, ...handoff.rejected];
      await this.refreshGuidance();
      this.#renderSession();
      this.status.textContent = rejected.length
        ? `Vorbelegung teilweise abgewiesen: ${rejected.join(", ")}`
        : handoff.applied
          ? "Vorbelegung übernommen – Varianten ausdrücklich vorbereiten"
          : "Setup bereit für Varianten";
    } catch (error) {
      this.status.textContent = errorMessage(error);
      this.prepareButton.disabled = true;
      this.refreshButton.disabled = true;
    }
  }

  /** Prepare a fresh transient batch while retaining an older stale batch on failure. */
  async prepare() {
    this.#setBusy(true);
    this.status.textContent = "Varianten werden vorbereitet …";
    try {
      const batch = await this.session.prepare((signal) =>
        this.api.post("playground/variant-batches", this.#variantRequest(), {
          signal,
        }),
      );
      this.inspectedDraftUid = "";
      this.#renderSession(true);
      this.workspace.show("variants");
      this.status.textContent = batch.diversity_exhausted
        ? `${batch.unique_count} eindeutige Varianten · Auswahlraum ausgeschöpft`
        : `${batch.unique_count} eindeutige Varianten bereit`;
      await this.refreshEvidence();
    } catch (error) {
      this.#renderSession();
      if (!(error instanceof DOMException && error.name === "AbortError"))
        this.status.textContent = errorMessage(error);
    } finally {
      this.#setBusy(false);
    }
  }

  /** Submit every selected reviewed variant exactly once. */
  async submit() {
    this.#reviewActiveVariant();
    const variants = this.session.selectedVariants().map(
      /** @param {Record<string, any>} variant */ (variant) => {
        const draftUid = String(variant.draft_uid || "");
        return (
          this.session.reviewedPayload(draftUid) ||
          variantGenerationPayload(variant)
        );
      },
    );
    if (!variants.length || !this.session.canSubmit) return;
    this.#setBusy(true);
    this.status.textContent = "Ausgewählte Varianten werden übergeben …";
    try {
      const batch = await this.session.submit((signal) =>
        this.api.post("generations/batch", { variants }, { signal }),
      );
      const submissions = Array.isArray(batch.submissions)
        ? batch.submissions
        : [];
      const failures = Array.isArray(batch.failures) ? batch.failures : [];
      this.#renderBatchResult(submissions, failures);
      this.status.textContent = failures.length
        ? `${submissions.length} übergeben · ${failures.length} fehlgeschlagen`
        : `${submissions.length} Varianten an ComfyUI übergeben`;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      this.result.dataset.state = "error";
      this.result.textContent = errorMessage(error);
      this.status.textContent = "Batch-Generierung fehlgeschlagen";
    } finally {
      this.#setBusy(false);
    }
  }

  /** @param {string} draftUid */
  inspectVariant(draftUid) {
    this.#reviewActiveVariant();
    if (!this.session.inspect(draftUid)) return;
    this.#renderSession(true);
    this.workspace.openInspector();
    void this.refreshEvidence();
  }

  /** @param {string} draftUid @param {boolean} selected */
  selectVariant(draftUid, selected) {
    if (!this.session.select(draftUid, selected)) return;
    this.#renderSession();
    this.#setBusy(false);
  }

  /** Retain the active edit as a reviewed variant payload. */
  variantEdited() {
    this.#reviewActiveVariant();
    void this.refreshPreview();
  }

  /** Refresh the authoritative rendered prompt for the active variant. */
  async refreshPreview() {
    const payload = this.inspector.promptPayload();
    if (!payload) return;
    this.previewRequests.cancelRequests();
    try {
      const rendered = await this.previewRequests.run((signal) =>
        this.api.post("playground/render-preview", payload, { signal }),
      );
      this.inspector.renderSnapshots(rendered);
      await this.refreshEvidence();
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        this.status.textContent = errorMessage(error);
    }
  }

  /** Refresh prompt and sampler evidence for the active concrete variant. */
  async refreshEvidence() {
    const prompt = this.inspector.promptPayload();
    const variant = this.session.activeVariant();
    if (!prompt || !variant) return;
    try {
      const evidence = await this.previewRequests.run((signal) =>
        this.api.post(
          "playground/evidence",
          { ...(variant.generation || {}), ...prompt },
          { signal },
        ),
      );
      this.inspector.renderEvidence(evidence);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        this.status.textContent = errorMessage(error);
    }
  }

  /** Refresh shared server-side render guidance for the setup. */
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
      if (!(error instanceof DOMException && error.name === "AbortError"))
        this.guidance.renderLoading(errorMessage(error));
    }
  }

  /** @param {"observed" | "predicted"} basis */
  guidanceModeChanged(basis) {
    this.guidanceBasis = basis;
    if (this.guidancePayload)
      this.controls.renderGuidance(this.guidancePayload, basis);
  }

  settingsChanged() {
    this.#setupChanged();
    this.guidanceRequests.cancel(this.guidanceTimer);
    this.guidanceTimer = this.guidanceRequests.schedule(
      () => void this.refreshGuidance(),
      180,
    );
  }

  promptSettingsChanged() {
    if (this.promptSourceImageUid) this.imagePromptEdited = true;
    this.#setupChanged();
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

  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.previewRequests.dispose();
    this.guidanceRequests.dispose();
    this.session.dispose();
    this.persistence.dispose();
    this.modes.dispose();
    this.controls.dispose();
    this.inspector.dispose();
    this.board.dispose();
    this.workspace.dispose();
    this.guidance.dispose();
  }

  #setupChanged() {
    this.session.markStale();
    this.previewRequests.cancelRequests();
    this.result.replaceChildren();
    delete this.result.dataset.state;
    this.persistence.schedule();
    this.#renderSession();
    this.#setBusy(false);
    this.status.textContent = this.session.hasVariants
      ? "Setup geändert – Varianten aktualisieren"
      : "Setup geändert – Varianten vorbereiten";
  }

  /** @param {boolean} [forceInspector] */
  #renderSession(forceInspector = false) {
    const state = this.session.snapshot();
    this.board.render(state);
    this.workspace.setVariantsAvailable(this.session.hasVariants);
    this.selectedCount.textContent = `${state.selectedDraftUids.size} ausgewählt`;
    this.variantSummary.textContent = this.session.hasVariants
      ? `${state.metadata.uniqueCount} eindeutig · ${state.metadata.repeatedCount} Wiederholungen`
      : "Noch kein Varianten-Batch";
    const active = this.session.activeVariant();
    if (!active) {
      this.inspectedDraftUid = "";
      this.inspector.clear();
      return;
    }
    const draftUid = String(active.draft_uid || "");
    if (!forceInspector && this.inspectedDraftUid === draftUid) return;
    const reviewed = this.session.reviewedPayload(draftUid);
    this.inspector.render(
      reviewed ? variantWithReviewedPayload(active, reviewed) : active,
    );
    this.inspectedDraftUid = draftUid;
  }

  #reviewActiveVariant() {
    const active = this.session.activeVariant();
    const payload = this.inspector.generationPayload();
    if (active && payload)
      this.session.review(String(active.draft_uid || ""), payload);
  }

  /** @param {boolean} busy */
  #setBusy(busy) {
    this.prepareButton.disabled = busy;
    this.refreshButton.disabled = busy || !this.session.hasVariants;
    this.submitButton.disabled = busy || !this.session.canSubmit;
    this.modes.setBusy(busy);
    this.controls.setBusy(busy);
  }

  #variantRequest() {
    const variant = this.controls.variantValue();
    const prompt = this.modes.value();
    if (!this.promptSourceImageUid) return { ...prompt, ...variant };
    if (!this.imagePromptEdited) {
      return {
        selections: [],
        loras: [],
        component_overrides: [],
        prompt_source: {
          mode: "image_snapshot",
          image_uid: this.promptSourceImageUid,
        },
        ...variant,
      };
    }
    return {
      ...prompt,
      prompt_source: {
        mode: "image_adapted",
        image_uid: this.promptSourceImageUid,
      },
      ...variant,
    };
  }

  /** @param {Array<Record<string, any>>} submissions @param {Array<Record<string, any>>} failures */
  #renderBatchResult(submissions, failures) {
    this.result.replaceChildren();
    this.result.dataset.state = failures.length ? "error" : "success";
    const byDraftUid = new Map();
    for (const item of submissions)
      byDraftUid.set(
        String(item.draft_uid),
        `${item.draft_uid} · ${item.generation_uid} · ${item.status}`,
      );
    for (const item of failures)
      byDraftUid.set(
        String(item.draft_uid),
        `${item.draft_uid} · Fehler: ${item.message}`,
      );
    const list = document.createElement("ul");
    for (const variant of this.session.selectedVariants()) {
      const item = document.createElement("li");
      item.textContent =
        byDraftUid.get(String(variant.draft_uid)) ||
        `${variant.draft_uid} · Keine Rückmeldung`;
      list.append(item);
    }
    this.result.append(list);
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
