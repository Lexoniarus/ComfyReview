/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (section: string, payload: Record<string, any>) => void, renderCompositionSetups: (compositionUid: string, payload: Record<string, any>) => void, clear: () => void}} ViewBoundary */

const sections = new Set(["overview", "scopes", "parameters", "combinations"]);

/** Orchestrate one canonical analytics report surface. */
export class AnalyticsController {
  /** @param {{section: string, api: ApiBoundary, requests: RequestBoundary, detailRequests: RequestBoundary, view: ViewBoundary, form: HTMLFormElement, model: HTMLInputElement, minimumSamples: HTMLInputElement, report: HTMLElement, status: HTMLElement, locationRef?: Location, historyRef?: History}} dependencies */
  constructor(dependencies) {
    this.section = sections.has(dependencies.section)
      ? dependencies.section
      : "overview";
    this.api = dependencies.api;
    this.requests = dependencies.requests;
    this.detailRequests = dependencies.detailRequests;
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
  }

  /** Restore URL filters and load the initial report. */
  async start() {
    const query = new URLSearchParams(this.locationRef.search);
    this.model.value = query.get("model") || "";
    this.minimumSamples.value =
      query.get("min_n") || defaultMinimum(this.section);
    this.viewName = query.get("view") || defaultView(this.section);
    this.parameter = query.get("parameter") || "";
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
    this.status.textContent = "Analyse wird geladen …";
    this.view.clear();
    const query = new URLSearchParams({
      model: this.model.value.trim(),
      min_n: normalizedMinimum(this.minimumSamples.value),
    });
    if (this.viewName) query.set("view", this.viewName);
    if (this.viewName === "values" && this.parameter) {
      query.set("parameter", this.parameter);
    }
    try {
      const payload = await this.requests.run((signal) =>
        this.api.get(`analytics/${this.section}?${query.toString()}`, {
          signal,
        }),
      );
      this.view.render(this.section, payload);
      this.status.textContent = "Analyse geladen";
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
    }
  }

  /** Release listeners and in-flight report requests. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.detailRequests.dispose();
    this.view.clear();
  }

  #writeUrl() {
    const query = new URLSearchParams();
    if (this.model.value.trim()) query.set("model", this.model.value.trim());
    query.set("min_n", normalizedMinimum(this.minimumSamples.value));
    if (this.viewName) query.set("view", this.viewName);
    if (this.viewName === "values" && this.parameter) {
      query.set("parameter", this.parameter);
    }
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
