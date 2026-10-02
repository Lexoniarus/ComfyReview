/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (section: string, payload: Record<string, any>) => HTMLElement, append: (payload: Record<string, any>) => void, renderCompositionSetups: (compositionUid: string, payload: Record<string, any>) => void, clear: () => void, dispose: () => void}} ViewBoundary */
/** @typedef {{start: (payload: Record<string, any>, sentinel: HTMLElement, operations: {fetchPage: (offset: number, signal: AbortSignal) => Promise<Record<string, any>>, appendPage: (payload: Record<string, any>) => void}) => void, reset: () => void, dispose: () => void}} CollectionBoundary */

const sections = new Set(["overview", "scopes", "parameters", "combinations"]);

/** Orchestrate one canonical analytics report surface. */
export class AnalyticsController {
  /** @param {{section: string, api: ApiBoundary, requests: RequestBoundary, detailRequests: RequestBoundary, collection: CollectionBoundary, view: ViewBoundary, form: HTMLFormElement, model: HTMLInputElement, minimumSamples: HTMLInputElement, report: HTMLElement, status: HTMLElement, locationRef?: Location, historyRef?: History}} dependencies */
  constructor(dependencies) {
    this.section = sections.has(dependencies.section)
      ? dependencies.section
      : "overview";
    this.api = dependencies.api;
    this.requests = dependencies.requests;
    this.detailRequests = dependencies.detailRequests;
    this.collection = dependencies.collection;
    this.view = dependencies.view;
    this.form = dependencies.form;
    this.model = dependencies.model;
    this.minimumSamples = dependencies.minimumSamples;
    this.report = dependencies.report;
    this.status = dependencies.status;
    this.locationRef = dependencies.locationRef || window.location;
    this.historyRef = dependencies.historyRef || window.history;
    this.abortController = new AbortController();
    this.viewName = defaultView(this.section);
    this.parameter = "";
    this.scopeKind = "character";
  }

  /** Restore URL filters and load the initial report. */
  async start() {
    const query = new URLSearchParams(this.locationRef.search);
    this.model.value = query.get("model") || "";
    this.minimumSamples.value =
      query.get("min_n") || defaultMinimum(this.section);
    this.viewName = query.get("view") || defaultView(this.section);
    this.parameter = query.get("parameter") || "";
    this.scopeKind = query.get("kind") || "character";
    this.form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        this.#writeUrl();
        void this.reload();
      },
      { signal: this.abortController.signal },
    );
    this.report.addEventListener(
      "click",
      (event) => void this.#handleReportClick(event),
      { signal: this.abortController.signal },
    );
    await this.reload();
  }

  /** Reload one server-computed analytics report. */
  async reload() {
    this.requests.cancelRequests();
    this.collection.reset();
    this.status.textContent = "Analyse wird geladen …";
    this.view.clear();
    try {
      const payload = await this.requests.run((signal) =>
        this.#loadPage(0, signal),
      );
      const sentinel = this.view.render(this.section, payload);
      this.collection.start(payload, sentinel, {
        fetchPage: (offset, signal) => this.#loadPage(offset, signal),
        appendPage: (page) => this.view.append(page),
      });
      this.status.textContent = resultStatus(payload);
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** Release listeners and in-flight report requests. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.detailRequests.dispose();
    this.collection.dispose();
    this.view.dispose();
  }

  #writeUrl() {
    const query = new URLSearchParams();
    if (this.model.value.trim()) query.set("model", this.model.value.trim());
    query.set("min_n", normalizedMinimum(this.minimumSamples.value));
    if (this.viewName) query.set("view", this.viewName);
    if (this.viewName === "values" && this.parameter) {
      query.set("parameter", this.parameter);
    }
    if (this.section === "scopes") query.set("kind", this.scopeKind);
    const suffix = query.toString();
    this.historyRef.replaceState(
      null,
      "",
      `${this.locationRef.pathname}?${suffix}`,
    );
  }

  /** @param {Event} event */
  async #handleReportClick(event) {
    if (!(event.target instanceof Element)) return;
    const viewControl = event.target.closest("[data-analytics-view]");
    if (viewControl instanceof HTMLElement) {
      this.viewName = viewControl.dataset.analyticsView || "";
      this.parameter = viewControl.dataset.analyticsParameter || "";
      this.#writeUrl();
      await this.reload();
      return;
    }
    const kindControl = event.target.closest("[data-analytics-scope-kind]");
    if (kindControl instanceof HTMLElement) {
      this.scopeKind = kindControl.dataset.analyticsScopeKind || "character";
      this.#writeUrl();
      await this.reload();
      return;
    }
    const detailsControl = event.target.closest("[data-composition-details]");
    if (!(detailsControl instanceof HTMLElement)) return;
    const compositionUid = detailsControl.dataset.compositionDetails || "";
    if (!compositionUid) return;
    this.detailRequests.cancelRequests();
    try {
      const payload = await this.detailRequests.run((signal) =>
        this.api.get(
          `analytics/combinations/${encodeURIComponent(compositionUid)}/render-setups?model=${encodeURIComponent(this.model.value.trim())}&min_n=1`,
          { signal },
        ),
      );
      this.view.renderCompositionSetups(compositionUid, payload);
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** @param {number} offset @param {AbortSignal} signal */
  #loadPage(offset, signal) {
    const query = new URLSearchParams({
      model: this.model.value.trim(),
      min_n: normalizedMinimum(this.minimumSamples.value),
      offset: String(offset),
      limit: "24",
    });
    if (this.viewName) query.set("view", this.viewName);
    if (this.viewName === "values" && this.parameter) {
      query.set("parameter", this.parameter);
    }
    if (this.section === "scopes") query.set("kind", this.scopeKind);
    return this.api.get(`analytics/${this.section}?${query.toString()}`, {
      signal,
    });
  }
}

/** @param {string} section */
function defaultMinimum(section) {
  if (section === "overview") return "5";
  if (section === "parameters") return "10";
  return "8";
}

/** @param {string} section */
function defaultView(section) {
  if (section === "parameters") return "summary";
  if (section === "combinations") return "prompt";
  return "";
}

/** @param {string} value */
function normalizedMinimum(value) {
  const parsed = Number.parseInt(value, 10);
  return String(Number.isFinite(parsed) ? Math.max(parsed, 0) : 0);
}

/** @param {unknown} error */
function isAbortError(error) {
  return error instanceof DOMException && error.name === "AbortError";
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Analyse konnte nicht geladen werden.";
}

/** @param {Record<string, any>} payload */
function resultStatus(payload) {
  const total = Number(payload.total);
  const items = Array.isArray(payload.items) ? payload.items.length : 0;
  return Number.isFinite(total)
    ? `${items} von ${total} Ergebnissen geladen`
    : "Analyse geladen";
}
