/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, patch: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[]) => void, select: (uid: string) => void, dispose: () => void}} BrowserBoundary */
/** @typedef {{create: () => void, render: (component: any, revisions: any[]) => void, setBusy: (busy: boolean) => void, dispose: () => void}} EditorBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, browser: BrowserBoundary, editor: EditorBoundary, requests: RequestBoundary, newButton: HTMLButtonElement, status: HTMLElement}} CatalogDependencies */

/** Orchestrate canonical catalog reads and reversible mutations. */
export class CatalogController {
  /** @param {CatalogDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.browser = dependencies.browser;
    this.editor = dependencies.editor;
    this.requests = dependencies.requests;
    this.newButton = dependencies.newButton;
    this.status = dependencies.status;
    this.currentUid = "";
    this.abortController = new AbortController();
  }

  /** Load all active and archived components and bind creation. */
  async start() {
    this.newButton.addEventListener("click", () => this.create(), {
      signal: this.abortController.signal,
    });
    await this.#reload();
  }

  /** Open the empty component form. */
  create() {
    this.currentUid = "";
    this.browser.select("");
    this.editor.create();
    this.status.textContent = "Neuer Katalogbaustein";
  }

  /** @param {string} componentUid */
  async select(componentUid) {
    this.requests.cancelRequests();
    this.status.textContent = "Revisionen werden geladen …";
    try {
      const [component, revisions] = await this.requests.run((signal) =>
        Promise.all([
          this.api.get(
            `catalog/components/${encodeURIComponent(componentUid)}`,
            {
              signal,
            },
          ),
          this.api.get(
            `catalog/components/${encodeURIComponent(componentUid)}/revisions`,
            { signal },
          ),
        ]),
      );
      this.currentUid = componentUid;
      this.browser.select(componentUid);
      this.editor.render(component, revisions.revisions || []);
      this.status.textContent = "Katalogeintrag geladen";
    } catch (error) {
      this.status.textContent = errorMessage(error);
    }
  }

  /** @param {Record<string, any>} payload */
  async save(payload) {
    this.editor.setBusy(true);
    this.status.textContent = "Katalogeintrag wird gespeichert …";
    try {
      const component = await this.requests.run((signal) =>
        this.currentUid
          ? this.api.put(
              `catalog/components/${encodeURIComponent(this.currentUid)}`,
              payload,
              { signal },
            )
          : this.api.post("catalog/components", payload, { signal }),
      );
      await this.#reload();
      await this.select(component.component_uid);
      this.status.textContent = "Katalogeintrag gespeichert";
    } catch (error) {
      this.status.textContent = errorMessage(error);
    } finally {
      this.editor.setBusy(false);
    }
  }

  /** @param {boolean} archived */
  async setArchived(archived) {
    if (!this.currentUid) return;
    this.editor.setBusy(true);
    try {
      const component = await this.requests.run((signal) =>
        this.api.patch(
          `catalog/components/${encodeURIComponent(this.currentUid)}`,
          { archived },
          { signal },
        ),
      );
      await this.#reload();
      await this.select(component.component_uid);
      this.status.textContent = archived
        ? "Katalogeintrag archiviert"
        : "Katalogeintrag wiederhergestellt";
    } catch (error) {
      this.status.textContent = errorMessage(error);
    } finally {
      this.editor.setBusy(false);
    }
  }

  /** Abort work and release browser collaborators. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.browser.dispose();
    this.editor.dispose();
  }

  async #reload() {
    try {
      const payload = await this.requests.run((signal) =>
        this.api.get("catalog/components?include_archived=true", { signal }),
      );
      this.browser.render(payload.components || []);
      this.status.textContent = `${(payload.components || []).length} Katalogeinträge`;
    } catch (error) {
      this.status.textContent = errorMessage(error);
    }
  }
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
