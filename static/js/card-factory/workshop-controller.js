const activeCandidateStatuses = new Set(["pending", "submitted"]);

/** @typedef {{session: (sessionId: string, options?: {signal?: AbortSignal}) => Promise<any>, generate: (sessionId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, accept: (sessionId: string, candidateId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, develop: (sessionId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>}} WorkshopApi */
/** @typedef {{root: HTMLElement, render: (session: Record<string, any>) => void, setBusy: (busy: boolean) => void, showError: (text: string) => void, dispose: () => void}} WorkshopView */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void, cancelRequests: () => void, dispose: () => void}} RequestBoundary */

/** Own revision-safe Card workshop commands and bounded candidate polling. */
export class CardWorkshopController {
  /** @param {{sessionId: string, api: WorkshopApi, view: WorkshopView, requests: RequestBoundary, documentRef?: Document, pollInterval?: number}} dependencies */
  constructor(dependencies) {
    this.sessionId = dependencies.sessionId;
    this.api = dependencies.api;
    this.view = dependencies.view;
    this.requests = dependencies.requests;
    this.documentRef = dependencies.documentRef || document;
    this.pollInterval = dependencies.pollInterval || 3000;
    /** @type {Record<string, any> | null} */
    this.session = null;
    this.pollTimer = null;
    this.abortController = new AbortController();
  }

  /** Bind controls and load the current persistent session. */
  async start() {
    const generate = requiredButton(
      this.view.root,
      "[data-generate-candidates]",
    );
    const develop = requiredButton(this.view.root, "[data-develop-card]");
    generate.addEventListener("click", () => void this.generate(), {
      signal: this.abortController.signal,
    });
    develop.addEventListener("click", () => void this.develop(), {
      signal: this.abortController.signal,
    });
    this.documentRef.addEventListener(
      "visibilitychange",
      () => this.#visibilityChanged(),
      { signal: this.abortController.signal },
    );
    await this.reload();
  }

  /** Synchronize and render one current session snapshot. */
  async reload() {
    this.requests.cancelRequests();
    this.requests.cancel(this.pollTimer);
    this.pollTimer = null;
    try {
      const session = await this.requests.run(
        (/** @type {AbortSignal} */ signal) =>
          this.api.session(this.sessionId, { signal }),
      );
      this.#acceptSnapshot(session);
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
    }
  }

  /** Reserve and submit four stable candidate slots. */
  async generate() {
    if (!this.session) return;
    const current = this.session;
    this.view.setBusy(true);
    try {
      const session = await this.requests.run(
        (/** @type {AbortSignal} */ signal) =>
          this.api.generate(this.sessionId, Number(current.revision), {
            signal,
          }),
      );
      this.#acceptSnapshot(session);
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
      await this.reload();
    }
  }

  /** Accept one server-authorized completed candidate. @param {string} candidateId */
  async accept(candidateId) {
    if (!this.session) return;
    const current = this.session;
    this.view.setBusy(true);
    try {
      const session = await this.requests.run(
        (/** @type {AbortSignal} */ signal) =>
          this.api.accept(
            this.sessionId,
            candidateId,
            Number(current.revision),
            { signal },
          ),
      );
      this.#acceptSnapshot(session);
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
      await this.reload();
    }
  }

  /** Advance exactly one tier through the server-owned development policy. */
  async develop() {
    if (!this.session) return;
    const current = this.session;
    this.view.setBusy(true);
    try {
      const session = await this.requests.run(
        (/** @type {AbortSignal} */ signal) =>
          this.api.develop(this.sessionId, Number(current.revision), {
            signal,
          }),
      );
      this.#acceptSnapshot(session);
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
      await this.reload();
    }
  }

  /** Dispose requests, timers, listeners and child view resources. */
  dispose() {
    this.abortController.abort();
    this.requests.cancel(this.pollTimer);
    this.requests.dispose();
    this.view.dispose();
  }

  /** @param {Record<string, any>} session */
  #acceptSnapshot(session) {
    this.session = session;
    this.view.render(session);
    this.#schedulePoll();
  }

  #schedulePoll() {
    this.requests.cancel(this.pollTimer);
    this.pollTimer = null;
    const candidates = Array.isArray(this.session?.candidates)
      ? this.session.candidates
      : [];
    const hasActive = candidates.some((candidate) =>
      activeCandidateStatuses.has(String(candidate.status)),
    );
    if (!hasActive || this.documentRef.visibilityState === "hidden") return;
    this.pollTimer = this.requests.schedule(
      () => void this.reload(),
      this.pollInterval,
    );
  }

  #visibilityChanged() {
    this.requests.cancel(this.pollTimer);
    this.pollTimer = null;
    if (this.documentRef.visibilityState !== "hidden") void this.reload();
  }
}

/** @param {ParentNode} root @param {string} selector */
function requiredButton(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLButtonElement))
    throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {unknown} error */
function isAbortError(error) {
  return error instanceof DOMException && error.name === "AbortError";
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
