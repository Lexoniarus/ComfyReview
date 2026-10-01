/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{render: (section: string, payload: Record<string, any>) => void, clear: () => void}} ViewBoundary */

const sections = new Set(["overview", "scopes", "parameters", "combinations"]);

/** Orchestrate one canonical analytics report surface. */
export class AnalyticsController {
  /** @param {{section: string, api: ApiBoundary, requests: RequestBoundary, view: ViewBoundary, form: HTMLFormElement, model: HTMLInputElement, minimumSamples: HTMLInputElement, status: HTMLElement, locationRef?: Location, historyRef?: History}} dependencies */
  constructor(dependencies) {
    this.section = sections.has(dependencies.section)
      ? dependencies.section
      : "overview";
    this.api = dependencies.api;
    this.requests = dependencies.requests;
    this.view = dependencies.view;
    this.form = dependencies.form;
    this.model = dependencies.model;
    this.minimumSamples = dependencies.minimumSamples;
    this.status = dependencies.status;
    this.locationRef = dependencies.locationRef || window.location;
    this.historyRef = dependencies.historyRef || window.history;
    this.abortController = new AbortController();
  }

  /** Restore URL filters and load the initial report. */
  async start() {
    const query = new URLSearchParams(this.locationRef.search);
    this.model.value = query.get("model") || "";
    this.minimumSamples.value =
      query.get("min_n") || defaultMinimum(this.section);
    this.form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        this.#writeUrl();
        void this.reload();
      },
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
    this.view.clear();
  }

  #writeUrl() {
    const query = new URLSearchParams();
    if (this.model.value.trim()) query.set("model", this.model.value.trim());
    query.set("min_n", normalizedMinimum(this.minimumSamples.value));
    const suffix = query.toString();
    this.historyRef.replaceState(
      null,
      "",
      `${this.locationRef.pathname}?${suffix}`,
    );
  }
}

/** @param {string} section */
function defaultMinimum(section) {
  if (section === "overview") return "5";
  if (section === "parameters") return "10";
  return "8";
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
