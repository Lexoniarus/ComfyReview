/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[]) => void, value: () => {selections: any[], seed: number | null}, dispose: () => void}} ModesBoundary */
/** @typedef {{render: (capabilities: any) => void, value: () => any, setBusy: (busy: boolean) => void, dispose: () => void}} ControlsBoundary */
/** @typedef {{render: (draft: any, draftUid: string) => void, generationPayload: (settings: any) => any, dispose: () => void}} DraftBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (payload: Record<string, any>) => void, dispose: () => void}} CombinationsBoundary */
/** @typedef {{api: ApiBoundary, modes: ModesBoundary, controls: ControlsBoundary, draft: DraftBoundary, combinations: CombinationsBoundary, requests: RequestBoundary, prepareButton: HTMLButtonElement, submitButton: HTMLButtonElement, status: HTMLElement, result: HTMLElement, newDraftUid: () => string}} PlaygroundDependencies */

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
    this.prepareButton = dependencies.prepareButton;
    this.submitButton = dependencies.submitButton;
    this.status = dependencies.status;
    this.result = dependencies.result;
    this.newDraftUid = dependencies.newDraftUid;
    this.abortController = new AbortController();
    this.hasDraft = false;
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
      const [catalog, capabilities, combinations] = await this.requests.run(
        (signal) =>
          Promise.all([
            this.api.get("catalog/components", { signal }),
            this.api.get("playground/capabilities", { signal }),
            this.api.get("playground/top-combinations", { signal }),
          ]),
      );
      this.modes.render(catalog.components || []);
      this.controls.render(capabilities);
      this.combinations.render(combinations);
      this.status.textContent = "Bereit für deinen Entwurf";
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
        this.api.post("playground/drafts", this.modes.value(), { signal }),
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
    this.modes.dispose();
    this.controls.dispose();
    this.draft.dispose();
    this.combinations.dispose();
  }

  /** @param {boolean} busy */
  #setBusy(busy) {
    this.prepareButton.disabled = busy;
    this.submitButton.disabled = busy || !this.hasDraft;
    this.controls.setBusy(busy);
  }
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
