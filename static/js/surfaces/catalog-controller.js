/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, patch: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (components: any[]) => void, select: (uid: string) => void, selectedCatalogKind: () => string, dispose: () => void}} BrowserBoundary */
/** @typedef {{create: (catalogKind?: string) => void, render: (component: any, revisions: any[]) => void, setBusy: (busy: boolean) => void, dispose: () => void}} EditorBoundary */
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
    this.currentKind = "component";
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
    this.currentKind = this.browser.selectedCatalogKind?.() || "component";
    this.browser.select("");
    this.editor.create(this.currentKind);
    this.status.textContent =
      this.currentKind === "lora" ? "Neue LoRA" : "Neuer Katalogbaustein";
  }

  /** @param {string} componentUid */
  async select(componentUid, catalogKind = "component") {
    this.requests.cancelRequests();
    this.status.textContent = "Revisionen werden geladen …";
    try {
      const segment = catalogKind === "lora" ? "loras" : "components";
      const [component, revisions] = await this.requests.run((signal) =>
        Promise.all([
          this.api.get(
            `catalog/${segment}/${encodeURIComponent(componentUid)}`,
            {
              signal,
            },
          ),
          this.api.get(
            `catalog/${segment}/${encodeURIComponent(componentUid)}/revisions`,
            { signal },
          ),
        ]),
      );
      this.currentUid = componentUid;
      this.currentKind = catalogKind;
      this.browser.select(componentUid);
      this.editor.render(
        { ...component, catalog_kind: catalogKind },
        revisions.revisions || [],
      );
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
      const isLora =
        payload.catalog_kind === "lora" || this.currentKind === "lora";
      const segment = isLora ? "loras" : "components";
      const body = { ...payload };
      delete body.catalog_kind;
      const component = await this.requests.run((signal) =>
        this.currentUid
          ? this.api.put(
              `catalog/${segment}/${encodeURIComponent(this.currentUid)}`,
              body,
              { signal },
            )
          : this.api.post(`catalog/${segment}`, body, { signal }),
      );
      await this.#reload();
      await this.select(
        String(component.component_uid || component.lora_uid),
        isLora ? "lora" : "component",
      );
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
          `catalog/${this.currentKind === "lora" ? "loras" : "components"}/${encodeURIComponent(this.currentUid)}`,
          { archived },
          { signal },
        ),
      );
      await this.#reload();
      await this.select(
        String(component.component_uid || component.lora_uid),
        this.currentKind,
      );
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
      const [componentPayload, loraPayload] = await this.requests.run(
        (signal) =>
          Promise.all([
            this.api.get("catalog/components?include_archived=true", {
              signal,
            }),
            this.api.get("catalog/loras?include_archived=true", { signal }),
          ]),
      );
      const components = componentPayload.components || [];
      const loras = (loraPayload.loras || []).map(
        (/** @type {any} */ lora) => ({
          ...lora,
          catalog_kind: "lora",
          kind: "lora",
          component_uid: lora.lora_uid,
          component_key: lora.provider_name,
          name: lora.display_name,
        }),
      );
      this.browser.render([...components, ...loras]);
      this.status.textContent = `${components.length} Prompt-Bausteine · ${loras.length} LoRAs`;
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
