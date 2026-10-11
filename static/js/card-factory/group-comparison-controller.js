/** @typedef {{group: (groupId: string, options?: {signal?: AbortSignal}) => Promise<any>, acceptCandidate: (groupId: string, candidateId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, rejectGroup: (groupId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, retryGroup: (groupId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>}} ComparisonApi */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, schedule: (callback: () => void, delay: number) => number|null, cancel: (timer: number|null) => void, cancelRequests: () => void, dispose: () => void}} RequestBoundary */

/** Own polling and mutations for one persisted Candidate group. */
export class CardCandidateGroupComparisonController {
  /** @param {{groupId: string, api: ComparisonApi, view: any, requests: RequestBoundary, locationRef?: Location, pollInterval?: number}} dependencies */
  constructor(dependencies) {
    this.groupId = dependencies.groupId;
    this.api = dependencies.api;
    this.view = dependencies.view;
    this.requests = dependencies.requests;
    this.locationRef = dependencies.locationRef || window.location;
    this.pollInterval = dependencies.pollInterval || 1500;
    this.group = null;
    this.timer = null;
    this.abortController = new AbortController();
  }

  /** Bind explicit group actions and load the current aggregate. */
  async start() {
    const reject = requiredButton(this.view.root, "[data-reject-group]");
    const retry = requiredButton(this.view.root, "[data-retry-group]");
    reject.addEventListener("click", () => void this.reject(), {
      signal: this.abortController.signal,
    });
    retry.addEventListener("click", () => void this.retry(), {
      signal: this.abortController.signal,
    });
    await this.reload();
  }

  /** Refresh one group and poll only while its worker lifecycle is active. */
  async reload() {
    this.requests.cancel(this.timer);
    this.timer = null;
    try {
      this.group = await this.requests.run((signal) =>
        this.api.group(this.groupId, { signal }),
      );
      this.view.render(this.group);
      if (["queued", "composing", "generating"].includes(this.group.status)) {
        this.timer = this.requests.schedule(
          () => void this.reload(),
          this.pollInterval,
        );
      }
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
    }
  }

  /** @param {string} candidateId */
  async accept(candidateId) {
    if (!this.group) return;
    await this.#mutate(async (signal) => {
      await this.api.acceptCandidate(
        this.groupId,
        candidateId,
        Number(this.group.revision),
        { signal },
      );
      this.locationRef.assign("/card-deck");
    });
  }

  /** Reject the complete comparison without changing a confirmed Card. */
  async reject() {
    if (!this.group) return;
    await this.#mutate(async (signal) => {
      this.group = await this.api.rejectGroup(
        this.groupId,
        Number(this.group.revision),
        { signal },
      );
      this.view.render(this.group);
    });
  }

  /** Discard an initial set and navigate to its fresh analysis group. */
  async retry() {
    if (!this.group) return;
    await this.#mutate(async (signal) => {
      const fresh = await this.api.retryGroup(
        this.groupId,
        Number(this.group.revision),
        { signal },
      );
      this.locationRef.assign(
        `/card-candidate-groups/${encodeURIComponent(String(fresh.group_id))}`,
      );
    });
  }

  /** Dispose listeners, polling, and active requests. */
  dispose() {
    this.abortController.abort();
    this.requests.cancel(this.timer);
    this.requests.dispose();
    this.view.dispose();
  }

  /** @param {(signal: AbortSignal) => Promise<void>} operation */
  async #mutate(operation) {
    this.view.setBusy(true);
    try {
      await this.requests.run(operation);
    } catch (error) {
      if (!isAbortError(error)) this.view.showError(errorMessage(error));
    } finally {
      this.view.setBusy(false);
    }
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
