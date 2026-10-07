/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{observe: (element: Element) => void, disconnect: () => void}} ObserverBoundary */

/** Own incremental analytics loading, observation and stale-request guards. */
export class AnalyticsCollectionController {
  /** @param {{requests: RequestBoundary, status: HTMLElement, observerFactory?: (callback: IntersectionObserverCallback) => ObserverBoundary}} dependencies */
  constructor(dependencies) {
    this.requests = dependencies.requests;
    this.fetchPage = null;
    this.appendPage = null;
    this.status = dependencies.status;
    this.observerFactory =
      dependencies.observerFactory ||
      ((callback) =>
        new IntersectionObserver(callback, { rootMargin: "600px" }));
    this.observer = null;
    this.sentinel = null;
    this.retry = null;
    this.keys = new Set();
    this.nextOffset = 0;
    this.total = 0;
    this.loading = false;
    this.disposed = false;
    this.revision = 0;
  }

  /** @param {Record<string, any>} payload @param {HTMLElement} sentinel @param {{fetchPage: (offset: number, signal: AbortSignal) => Promise<Record<string, any>>, appendPage: (payload: Record<string, any>) => void}} operations */
  start(payload, sentinel, operations) {
    this.reset();
    this.sentinel = sentinel;
    this.fetchPage = operations.fetchPage;
    this.appendPage = operations.appendPage;
    const items = arrayItems(payload);
    for (const item of items) this.keys.add(itemKey(item));
    this.nextOffset = normalizedNumber(payload.offset) + items.length;
    this.total = normalizedNumber(payload.total);
    if (this.nextOffset >= this.total) return;
    this.observer = this.observerFactory((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void this.loadNext();
    });
    this.observer.observe(sentinel);
  }

  /** Load one page and ignore duplicate or stale entries. */
  async loadNext() {
    if (
      this.loading ||
      this.disposed ||
      !this.fetchPage ||
      !this.appendPage ||
      this.nextOffset >= this.total
    ) {
      return;
    }
    this.loading = true;
    this.#removeRetry();
    const revision = this.revision;
    this.status.textContent = "Weitere Ergebnisse werden geladen …";
    try {
      const fetchPage = this.fetchPage;
      const appendPage = this.appendPage;
      const payload = await this.requests.run((signal) =>
        fetchPage(this.nextOffset, signal),
      );
      if (this.disposed || revision !== this.revision) return;
      const uniqueItems = arrayItems(payload).filter((item) => {
        const key = itemKey(item);
        if (this.keys.has(key)) return false;
        this.keys.add(key);
        return true;
      });
      appendPage({ ...payload, items: uniqueItems });
      this.nextOffset =
        normalizedNumber(payload.offset) + arrayItems(payload).length;
      this.total = normalizedNumber(payload.total);
      this.status.textContent = `${Math.min(this.nextOffset, this.total)} von ${this.total} Ergebnissen geladen`;
      if (this.nextOffset >= this.total) {
        const observer = this.observer;
        if (observer) observer.disconnect();
      }
    } catch (error) {
      const sentinel = this.sentinel;
      if (
        !isAbortError(error) &&
        !this.disposed &&
        revision === this.revision &&
        sentinel
      ) {
        this.status.textContent = errorMessage(error);
        this.#showRetry(sentinel);
      }
    } finally {
      if (revision === this.revision) this.loading = false;
    }
  }

  /** Cancel the active page and detach its observer. */
  reset() {
    this.revision += 1;
    this.requests.cancelRequests();
    this.observer?.disconnect();
    this.observer = null;
    this.sentinel = null;
    this.keys.clear();
    this.nextOffset = 0;
    this.total = 0;
    this.loading = false;
    this.fetchPage = null;
    this.appendPage = null;
    this.#removeRetry();
  }

  /** Release every owned resource. */
  dispose() {
    this.disposed = true;
    this.reset();
    this.requests.dispose();
  }

  /** @param {HTMLElement} sentinel */
  #showRetry(sentinel) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button analytics-retry";
    button.textContent = "Erneut versuchen";
    button.addEventListener("click", () => void this.loadNext(), {
      once: true,
    });
    sentinel.before(button);
    this.retry = button;
  }

  #removeRetry() {
    this.retry?.remove();
    this.retry = null;
  }
}

/** @param {Record<string, any>} payload */
function arrayItems(payload) {
  return Array.isArray(payload.items) ? payload.items : [];
}

/** @param {Record<string, any>} item */
function itemKey(item) {
  return String(
    item.component_uid ||
      item.composition_uid ||
      item.setup_key ||
      (item.settings ? JSON.stringify(item.settings) : "") ||
      `${item.parameter || "item"}:${item.value || ""}`,
  );
}

/** @param {unknown} value */
function normalizedNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(0, Math.trunc(number)) : 0;
}

/** @param {unknown} error */
function isAbortError(error) {
  return error instanceof DOMException && error.name === "AbortError";
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Weitere Ergebnisse konnten nicht geladen werden.";
}
