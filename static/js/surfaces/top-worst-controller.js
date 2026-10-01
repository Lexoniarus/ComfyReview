/** @typedef {import("../scopes/url-state.js").ScopeUrlState} ScopeUrlState */
/** @typedef {{get: (path: string, options: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{subscribe: (listener: (state: ScopeUrlState) => void) => () => void, start: () => void, update: (patch: Partial<ScopeUrlState>) => void, dispose: () => void}} ScopeStateBoundary */
/** @typedef {{render: (facets: any[], selected: string[], classification: string) => void, dispose: () => void}} ScopeNavigatorBoundary */
/** @typedef {{render: (facets: any[], selected: string[]) => void, dispose: () => void}} ActiveScopesBoundary */
/** @typedef {{loading: () => void, render: (items: any[], offset: number) => void, error: (message: string) => void, dispose: () => void}} ImageGridBoundary */
/** @typedef {{render: (total: number, offset: number, limit: number) => void, dispose: () => void}} PaginationBoundary */
/** @typedef {{loading: () => void, render: (image: any) => void, error: (message: string) => void}} InspectorBoundary */
/** @typedef {{dispose: () => void}} ViewerBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, state: ScopeStateBoundary, navigator: ScopeNavigatorBoundary, activeScopes: ActiveScopesBoundary, grid: ImageGridBoundary, pagination: PaginationBoundary, inspector: InspectorBoundary, viewer: ViewerBoundary, facetRequests: RequestBoundary, rankingRequests: RequestBoundary, contextRequests: RequestBoundary, root: HTMLElement}} TopWorstDependencies */

/** Orchestrate the Top/Worst surface through focused collaborators. */
export class TopWorstController {
  /** @param {TopWorstDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.state = dependencies.state;
    this.navigator = dependencies.navigator;
    this.activeScopes = dependencies.activeScopes;
    this.grid = dependencies.grid;
    this.pagination = dependencies.pagination;
    this.inspector = dependencies.inspector;
    this.viewer = dependencies.viewer;
    this.facetRequests = dependencies.facetRequests;
    this.rankingRequests = dependencies.rankingRequests;
    this.contextRequests = dependencies.contextRequests;
    this.root = dependencies.root;
    this.events = new AbortController();
    /** @type {(() => void) | null} */
    this.unsubscribe = null;
  }

  /** Bind state and load the current surface. */
  start() {
    this.unsubscribe = this.state.subscribe((state) => {
      void this.#load(state);
    });
    this.root.addEventListener("click", (event) => this.#handleAction(event), {
      signal: this.events.signal,
    });
    this.state.start();
  }

  /** @param {string} imageUid */
  async selectImage(imageUid) {
    this.contextRequests.cancelRequests();
    this.inspector.loading();
    try {
      const image = await this.contextRequests.run((signal) =>
        this.api.get(`images/${encodeURIComponent(imageUid)}`, { signal }),
      );
      this.inspector.render(image);
      this.root.classList.add("is-inspector-open");
    } catch (error) {
      if (!isAbortError(error)) {
        this.inspector.error(errorMessage(error));
      }
    }
  }

  /** Abort requests and release every owned collaborator. */
  dispose() {
    if (this.unsubscribe) this.unsubscribe();
    this.events.abort();
    this.facetRequests.dispose();
    this.rankingRequests.dispose();
    this.contextRequests.dispose();
    this.navigator.dispose();
    this.activeScopes.dispose();
    this.grid.dispose();
    this.pagination.dispose();
    this.viewer.dispose();
    this.state.dispose();
  }

  /** @param {ScopeUrlState} state */
  async #load(state) {
    this.#reflectMode(state.mode);
    this.grid.loading();
    this.facetRequests.cancelRequests();
    this.rankingRequests.cancelRequests();
    const query = queryString(state);
    const facetsPromise = this.facetRequests.run((signal) =>
      this.api.get(`scopes/facets${query}`, { signal }),
    );
    const rankingsPromise = this.rankingRequests.run((signal) =>
      this.api.get(`rankings${query}`, { signal }),
    );
    try {
      const [facetPayload, rankingPayload] = await Promise.all([
        facetsPromise,
        rankingsPromise,
      ]);
      this.navigator.render(
        facetPayload.facets,
        state.scopes,
        state.classification,
      );
      this.activeScopes.render(facetPayload.facets, state.scopes);
      this.grid.render(rankingPayload.items, rankingPayload.offset);
      this.pagination.render(
        rankingPayload.total,
        rankingPayload.offset,
        rankingPayload.limit,
      );
      const count = this.root.querySelector("[data-result-count]");
      if (count) count.textContent = `${rankingPayload.total} Bilder`;
    } catch (error) {
      if (!isAbortError(error)) {
        this.grid.error(errorMessage(error));
      }
    }
  }

  /** @param {Event} event */
  #handleAction(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const action = target.closest("[data-surface-action]");
    if (!(action instanceof HTMLElement)) return;
    const value = action.dataset.surfaceAction;
    if (value === "top" || value === "worst") {
      this.state.update({ mode: value });
    } else if (value === "toggle-scopes") {
      this.#toggleRail("scope");
    } else if (value === "toggle-inspector") {
      this.#toggleRail("inspector");
    }
  }

  /** @param {"scope" | "inspector"} rail */
  #toggleRail(rail) {
    const openedClass =
      rail === "scope" ? "is-scope-open" : "is-inspector-open";
    const otherClass = rail === "scope" ? "is-inspector-open" : "is-scope-open";
    const shouldOpen = !this.root.classList.contains(openedClass);
    this.root.classList.toggle(openedClass, shouldOpen);
    if (shouldOpen) this.root.classList.remove(otherClass);
    this.#reflectRailState("scope", "is-scope-open");
    this.#reflectRailState("inspector", "is-inspector-open");
  }

  /** @param {string} rail @param {string} openedClass */
  #reflectRailState(rail, openedClass) {
    const action = rail === "scope" ? "toggle-scopes" : "toggle-inspector";
    const button = this.root.querySelector(`[data-surface-action='${action}']`);
    if (button) {
      button.setAttribute(
        "aria-expanded",
        String(this.root.classList.contains(openedClass)),
      );
    }
  }

  /** @param {string} mode */
  #reflectMode(mode) {
    for (const button of this.root.querySelectorAll(
      "[data-surface-action='top'], [data-surface-action='worst']",
    )) {
      const selected =
        button instanceof HTMLElement && button.dataset.surfaceAction === mode;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    }
  }
}

/** @param {ScopeUrlState} state */
function queryString(state) {
  const parameters = new URLSearchParams();
  state.scopes.forEach((scope) => parameters.append("scope", scope));
  parameters.set("classification", state.classification);
  if (state.model) parameters.set("model", state.model);
  if (state.checkpoint) parameters.set("checkpoint", state.checkpoint);
  if (state.setKey) parameters.set("set_key", state.setKey);
  parameters.set("mode", state.mode);
  parameters.set("offset", String(state.offset));
  parameters.set("limit", "48");
  return `?${parameters.toString()}`;
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
