/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{status: () => string, render: (items: any[]) => void, select: (uid: string) => void, dispose: () => void}} ListBoundary */
/** @typedef {{render: (detail: any) => void, clear: () => void, dispose: () => void}} DetailBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, schedule: (callback: () => void, delay: number) => number | null, cancel: (timer: number | null) => void, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, list: ListBoundary, detail: DetailBoundary, requests: RequestBoundary, status: HTMLElement, documentRef?: Document, pollInterval?: number}} GenerationDependencies */

const activeStatuses = new Set([
  "prepared",
  "submitting",
  "submitted",
  "running",
  "reconciliation_required",
]);

/** Orchestrate persisted generation lifecycle reads and reconciliation. */
export class GenerationsController {
  /** @param {GenerationDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.list = dependencies.list;
    this.detail = dependencies.detail;
    this.requests = dependencies.requests;
    this.status = dependencies.status;
    this.documentRef = dependencies.documentRef || document;
    this.pollInterval = dependencies.pollInterval || 5000;
    this.abortController = new AbortController();
    this.pollTimer = null;
    this.selectedUid = "";
    this.hasActiveItems = false;
  }

  /** Load lifecycle state and start visibility-aware polling. */
  async start() {
    this.documentRef.addEventListener(
      "visibilitychange",
      () => this.#visibilityChanged(),
      { signal: this.abortController.signal },
    );
    this.detail.clear();
    await this.reload();
  }

  /** Reload the current persisted status selection. */
  async reload() {
    this.requests.cancelRequests();
    this.requests.cancel(this.pollTimer);
    this.pollTimer = null;
    this.status.textContent = "Generierungen werden geladen …";
    const selectedStatus = this.list.status();
    const query = new URLSearchParams({ limit: "100" });
    if (selectedStatus) query.set("status", selectedStatus);
    try {
      const page = await this.requests.run((signal) =>
        this.api.get(`generations?${query.toString()}`, { signal }),
      );
      /** @type {Array<Record<string, any>>} */
      const items = Array.isArray(page.items) ? page.items : [];
      this.list.render(items);
      this.hasActiveItems = items.some((item) =>
        activeStatuses.has(String(item.status)),
      );
      this.status.textContent = `${page.total || 0} kanonische Generierungen`;
      this.#schedulePoll();
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** @param {string} generationUid */
  async select(generationUid) {
    this.requests.cancelRequests();
    this.selectedUid = generationUid;
    this.list.select(generationUid);
    this.status.textContent = "Details werden geladen …";
    try {
      const detail = await this.requests.run((signal) =>
        this.api.get(`generations/${encodeURIComponent(generationUid)}`, {
          signal,
        }),
      );
      if (this.selectedUid !== generationUid) return;
      this.detail.render(detail);
      this.status.textContent = "Generierung geladen";
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** @param {string} generationUid @param {string | null} promptId */
  async reconcile(generationUid, promptId) {
    this.status.textContent = "ComfyUI-Status wird abgeglichen …";
    try {
      await this.requests.run((signal) =>
        this.api.post(
          `generations/${encodeURIComponent(generationUid)}/reconcile`,
          { prompt_id: promptId },
          { signal },
        ),
      );
      await this.reload();
      await this.select(generationUid);
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** Abort requests, polling and component listeners. */
  dispose() {
    this.abortController.abort();
    this.requests.cancel(this.pollTimer);
    this.requests.dispose();
    this.list.dispose();
    this.detail.dispose();
  }

  #schedulePoll() {
    if (this.documentRef.visibilityState === "hidden" || !this.hasActiveItems) {
      return;
    }
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
