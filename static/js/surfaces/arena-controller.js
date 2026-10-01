/** @typedef {import("../scopes/url-state.js").ScopeUrlState} ScopeUrlState */
/** @typedef {{get: (path: string, options: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{subscribe: (listener: (state: ScopeUrlState) => void) => () => void, start: () => void, dispose: () => void}} ScopeStateBoundary */
/** @typedef {{render: (facets: any[], selected: string[], classification: string) => void, dispose: () => void}} NavigatorBoundary */
/** @typedef {{render: (facets: any[], selected: string[]) => void, dispose: () => void}} ActiveScopesBoundary */
/** @typedef {{loading: () => void, render: (pair: any) => void, empty: () => void, error: (message: string) => void, setBusy: (busy: boolean) => void, dispose: () => void}} BoardBoundary */
/** @typedef {{render: (image: any) => void, empty: () => void, error: (message: string) => void}} InspectorBoundary */
/** @typedef {{open: (url: string) => void, dispose: () => void}} ViewerBoundary */
/** @typedef {{open: (rail: "scope" | "inspector") => void, dispose: () => void}} RailsBoundary */
/** @typedef {{dispose: () => void}} DisposableBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, state: ScopeStateBoundary, navigator: NavigatorBoundary, activeScopes: ActiveScopesBoundary, board: BoardBoundary, inspector: InspectorBoundary, viewer: ViewerBoundary, rails: RailsBoundary, keyboard: DisposableBoundary, readRequests: RequestBoundary, mutationRequests: RequestBoundary, status: HTMLElement}} ArenaDependencies */

/** Orchestrate canonical Arena pair reads and decisions. */
export class ArenaController {
  /** @param {ArenaDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.state = dependencies.state;
    this.navigator = dependencies.navigator;
    this.activeScopes = dependencies.activeScopes;
    this.board = dependencies.board;
    this.inspector = dependencies.inspector;
    this.viewer = dependencies.viewer;
    this.rails = dependencies.rails;
    this.keyboard = dependencies.keyboard;
    this.readRequests = dependencies.readRequests;
    this.mutationRequests = dependencies.mutationRequests;
    this.status = dependencies.status;
    /** @type {ScopeUrlState | null} */
    this.currentState = null;
    /** @type {{left: Record<string, unknown>, right: Record<string, unknown>} | null} */
    this.currentPair = null;
    /** @type {(() => void) | null} */
    this.unsubscribe = null;
    this.isMutating = false;
  }

  /** Bind scope state and load the first pair. */
  start() {
    this.unsubscribe = this.state.subscribe((state) => {
      this.currentState = state;
      void this.#load(state);
    });
    this.state.start();
  }

  /** @param {"left" | "right"} side */
  async recordDecision(side) {
    if (!this.currentPair || this.isMutating) return;
    this.isMutating = true;
    this.board.setBusy(true);
    this.status.textContent = "Entscheidung wird gespeichert …";
    try {
      await this.mutationRequests.run((signal) =>
        this.api.post(
          "arena/decisions",
          {
            left_image_uid: this.currentPair?.left.image_uid,
            right_image_uid: this.currentPair?.right.image_uid,
            winner_side: side,
          },
          { signal },
        ),
      );
      if (this.currentState) await this.#load(this.currentState);
    } catch (error) {
      if (!isAbortError(error)) {
        this.board.setBusy(false);
        this.status.textContent = errorMessage(error);
      }
    } finally {
      this.isMutating = false;
    }
  }

  /** @param {Record<string, unknown>} image */
  inspect(image) {
    this.inspector.render(image);
    this.rails.open("inspector");
  }

  /** @param {string} url */
  expand(url) {
    this.viewer.open(url);
  }

  /** Abort work and release every collaborator. */
  dispose() {
    if (this.unsubscribe) this.unsubscribe();
    this.readRequests.dispose();
    this.mutationRequests.dispose();
    this.navigator.dispose();
    this.activeScopes.dispose();
    this.board.dispose();
    this.viewer.dispose();
    this.rails.dispose();
    this.keyboard.dispose();
    this.state.dispose();
  }

  /** @param {ScopeUrlState} state */
  async #load(state) {
    this.readRequests.cancelRequests();
    this.board.loading();
    this.status.textContent = "Paar wird geladen …";
    const query = queryString(state);
    try {
      const [facetPayload, pair] = await this.readRequests.run(async (signal) =>
        Promise.all([
          this.api.get(`scopes/facets${query}`, { signal }),
          this.api.get(`arena/pair${query}`, { signal }),
        ]),
      );
      this.navigator.render(
        facetPayload.facets,
        state.scopes,
        state.classification,
      );
      this.activeScopes.render(facetPayload.facets, state.scopes);
      this.currentPair = pair;
      if (pair) {
        this.board.render(pair);
        this.inspector.render(pair.left);
        this.status.textContent = "Wähle das stärkere Bild";
      } else {
        this.board.empty();
        this.inspector.empty();
        this.status.textContent = "Keine offene Paarung";
      }
    } catch (error) {
      if (!isAbortError(error)) {
        const message = errorMessage(error);
        this.currentPair = null;
        this.board.error(message);
        this.inspector.error(message);
        this.status.textContent = "Laden fehlgeschlagen";
      }
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
