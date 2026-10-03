/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[]) => void, applyIntent: (intent: Record<string, any>) => void, value: () => {selections: any[], seed: number | null}, dispose: () => void}} ModesBoundary */
/** @typedef {{render: (capabilities: any) => void, applyIntent: (intent: Record<string, any>) => void, value: () => any, setBusy: (busy: boolean) => void, dispose: () => void}} ControlsBoundary */
/** @typedef {{render: (draft: any, draftUid: string) => void, promptPayload: () => any, renderSnapshots: (payload: any) => void, generationPayload: (settings: any) => any, dispose: () => void}} DraftBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (payload: Record<string, any>) => void, dispose: () => void}} CombinationsBoundary */
/** @typedef {{api: ApiBoundary, modes: ModesBoundary, controls: ControlsBoundary, draft: DraftBoundary, combinations: CombinationsBoundary, requests: RequestBoundary, previewRequests: RequestBoundary & {cancelRequests: () => void}, prepareButton: HTMLButtonElement, submitButton: HTMLButtonElement, status: HTMLElement, result: HTMLElement, newDraftUid: () => string, intent?: Record<string, any>}} PlaygroundDependencies */

/** Orchestrate catalog draft preparation and native generation submission. */
export class PlaygroundController {
  /** @param {PlaygroundDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.modes = dependencies.modes;
    this.controls = dependencies.controls;
    this.draft = dependencies.draft;
    this.combinations = dependencies.combinations;
    this.requests = dependencies.requests;
    this.previewRequests = dependencies.previewRequests;
    this.prepareButton = dependencies.prepareButton;
    this.submitButton = dependencies.submitButton;
    this.status = dependencies.status;
    this.result = dependencies.result;
    this.newDraftUid = dependencies.newDraftUid;
    this.intent = dependencies.intent || {};
    this.draftReference = null;
    this.abortController = new AbortController();
    this.hasDraft = false;
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
      const [catalog, capabilities, profiles, combinations] =
        await this.requests.run((signal) =>
          Promise.all([
            this.api.get("playground/components", { signal }),
            this.api.get("playground/capabilities", { signal }),
            this.api.get("settings/generation-profiles", { signal }),
            this.api.get("playground/top-combinations", { signal }),
          ]),
        );
      this.modes.render(catalog.components || []);
      this.controls.render({
        ...capabilities,
        profiles: profiles.items || [],
      });
      this.combinations.render(combinations);
      await this.#applyIntent();
      this.status.textContent = hasPrefill(this.intent)
        ? "Vorbelegung übernommen – erstelle den Entwurf ausdrücklich"
        : "Bereit für deinen Entwurf";
    } catch (error) {
      this.status.textContent = errorMessage(error);
      this.prepareButton.disabled = true;
    }
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
          this.draftReference || this.modes.value(),
          { signal },
        ),
      );
      this.draft.render(draft, this.newDraftUid());
      this.hasDraft = true;
      this.status.textContent = "Entwurf bereit zur Prüfung";
    } catch (error) {
      this.hasDraft = false;
      this.status.textContent = errorMessage(error);
    } finally {
      this.#setBusy(false);
    }
  }

  /** Submit the reviewed snapshot through the native generation service. */
  async submit() {
    const payload = this.draft.generationPayload(this.controls.value());
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
    this.modes.dispose();
    this.controls.dispose();
    this.draft.dispose();
    this.combinations.dispose();
  }

  /** Use current mode controls after the user changes a prompt prefill. */
  clearDraftReference() {
    this.draftReference = null;
  }

  /** @param {boolean} busy */
  #setBusy(busy) {
    this.prepareButton.disabled = busy;
    this.submitButton.disabled = busy || !this.hasDraft;
    this.controls.setBusy(busy);
  }

  async #applyIntent() {
    let intent = this.intent;
    if (intent.imageUid) {
      const image = await this.requests.run((signal) =>
        this.api.get(`images/${encodeURIComponent(intent.imageUid)}`, {
          signal,
        }),
      );
      intent = imageIntent(image);
      this.intent = intent;
    }
    this.modes.applyIntent(intent);
    this.controls.applyIntent(intent);
    if (Array.isArray(intent.revisionUids) && intent.revisionUids.length) {
      this.draftReference = { revision_uids: intent.revisionUids };
    } else if (intent.compositionUid) {
      this.draftReference = { composition_uid: intent.compositionUid };
    }
  }
}

/** @param {Record<string, any>} image */
function imageIntent(image) {
  const scopes = Array.isArray(image.scopes) ? image.scopes : [];
  const settings =
    image.generation_settings && typeof image.generation_settings === "object"
      ? image.generation_settings
      : {};
  return {
    imageUid: String(image.image_uid || ""),
    componentUids: scopes.map((scope) => String(scope.component_uid || "")),
    revisionUids: scopes.map((scope) => String(scope.revision_uid || "")),
    checkpoint: settings.checkpoint,
    sampler: settings.sampler,
    scheduler: settings.scheduler,
    seedMode: "fixed",
    seed: settings.seed,
    steps_min: settings.steps,
    steps_max: settings.steps,
    cfg_min: settings.cfg,
    cfg_max: settings.cfg,
    denoise: settings.denoise,
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
