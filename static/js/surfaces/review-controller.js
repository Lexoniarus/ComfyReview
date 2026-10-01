/** @typedef {import("../scopes/url-state.js").ScopeUrlState} ScopeUrlState */
/** @typedef {{get: (path: string, options: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{subscribe: (listener: (state: ScopeUrlState) => void) => () => void, start: () => void, update: (patch: Partial<ScopeUrlState>) => void, dispose: () => void}} ScopeStateBoundary */
/** @typedef {{render: (facets: any[], selected: string[], classification: string) => void, dispose: () => void}} ScopeNavigatorBoundary */
/** @typedef {{render: (facets: any[], selected: string[]) => void, dispose: () => void}} ActiveScopesBoundary */
/** @typedef {{loading: (message?: string) => void, render: (image: any) => void, empty: () => void, error: (message: string) => void, setBusy: (busy: boolean) => void, dispose: () => void}} ReviewStageBoundary */
/** @typedef {{render: (image: any) => void, empty: () => void, error: (message: string) => void}} InspectorBoundary */
/** @typedef {{open: (url: string) => void, dispose: () => void}} ViewerBoundary */
/** @typedef {{open: (rail: "scope" | "inspector") => void, dispose: () => void}} RailsBoundary */
/** @typedef {{confirm: (message: string) => Promise<boolean>, dispose: () => void}} DialogBoundary */
/** @typedef {{dispose: () => void}} KeyboardBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, state: ScopeStateBoundary, navigator: ScopeNavigatorBoundary, activeScopes: ActiveScopesBoundary, stage: ReviewStageBoundary, inspector: InspectorBoundary, viewer: ViewerBoundary, rails: RailsBoundary, dialog: DialogBoundary, keyboard: KeyboardBoundary, readRequests: RequestBoundary, mutationRequests: RequestBoundary, status: HTMLElement}} ReviewDependencies */

/** Orchestrate canonical review selection and mutations. */
export class ReviewController {
  /** @param {ReviewDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.state = dependencies.state;
    this.navigator = dependencies.navigator;
    this.activeScopes = dependencies.activeScopes;
    this.stage = dependencies.stage;
    this.inspector = dependencies.inspector;
    this.viewer = dependencies.viewer;
    this.rails = dependencies.rails;
    this.dialog = dependencies.dialog;
    this.keyboard = dependencies.keyboard;
    this.readRequests = dependencies.readRequests;
    this.mutationRequests = dependencies.mutationRequests;
    this.status = dependencies.status;
    /** @type {ScopeUrlState | null} */
    this.currentState = null;
    /** @type {Record<string, unknown> | null} */
    this.currentImage = null;
    /** @type {(() => void) | null} */
    this.unsubscribe = null;
    this.isMutating = false;
  }

  /** Bind scope state and load the first canonical candidate. */
  start() {
    this.unsubscribe = this.state.subscribe((state) => {
      this.currentState = state;
      void this.#load(state);
    });
    this.state.start();
  }

  /** @param {number} rating */
  async submitRating(rating) {
    if (!this.currentImage || this.isMutating) return;
    await this.#mutate("Bewertung wird gespeichert …", (signal) =>
      this.api.post(
        "reviews",
        { image_uid: this.currentImage?.image_uid, rating },
        { signal },
      ),
    );
  }

  /** Ask for confirmation and delete the current image when accepted. */
  async deleteCurrent() {
    if (!this.currentImage || this.isMutating) return;
    const confirmed = await this.dialog.confirm(
      "Das Bild wird reversibel aus dem aktiven Output entfernt.",
    );
    if (!confirmed || !this.currentImage) return;
    const imageUid = String(this.currentImage.image_uid || "");
    await this.#mutate("Bild wird gelöscht …", (signal) =>
      this.api.post(
        `images/${encodeURIComponent(imageUid)}/delete`,
        {},
        { signal },
      ),
    );
  }

  /** @param {string} url */
  expand(url) {
    this.viewer.open(url);
  }

  /** Abort requests and release every owned collaborator. */
  dispose() {
    if (this.unsubscribe) this.unsubscribe();
    this.readRequests.dispose();
    this.mutationRequests.dispose();
    this.navigator.dispose();
    this.activeScopes.dispose();
    this.stage.dispose();
    this.viewer.dispose();
    this.rails.dispose();
    this.dialog.dispose();
    this.keyboard.dispose();
    this.state.dispose();
  }

  /** @param {ScopeUrlState} state */
  async #load(state) {
    this.readRequests.cancelRequests();
    this.stage.loading();
    this.status.textContent = "Nächstes Bild wird geladen …";
    const query = queryString(state);
    try {
      const [facetPayload, candidate] = await this.readRequests.run(
        async (signal) =>
          Promise.all([
            this.api.get(`scopes/facets${query}`, { signal }),
            this.api.get(`review/candidate${query}`, { signal }),
          ]),
      );
      this.navigator.render(
        facetPayload.facets,
        state.scopes,
        state.classification,
      );
      this.activeScopes.render(facetPayload.facets, state.scopes);
      this.currentImage = candidate;
      if (candidate) {
        this.stage.render(candidate);
        this.inspector.render(candidate);
        this.status.textContent = "Bereit für deine Bewertung";
      } else {
        this.stage.empty();
        this.inspector.empty();
        this.status.textContent = "Keine Bilder in dieser Auswahl";
      }
    } catch (error) {
      if (!isAbortError(error)) {
        const message = errorMessage(error);
        this.currentImage = null;
        this.stage.error(message);
        this.inspector.error(message);
        this.status.textContent = "Laden fehlgeschlagen";
      }
    }
  }

  /** @param {string} message @param {(signal: AbortSignal) => Promise<any>} operation */
  async #mutate(message, operation) {
    this.isMutating = true;
    this.stage.setBusy(true);
    this.status.textContent = message;
    try {
      await this.mutationRequests.run(operation);
      if (this.currentState) await this.#load(this.currentState);
    } catch (error) {
      if (!isAbortError(error)) {
        this.stage.setBusy(false);
        this.status.textContent = errorMessage(error);
      }
    } finally {
      this.isMutating = false;
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
