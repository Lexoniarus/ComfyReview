/** @typedef {{sources: (options: {offset: number, limit: number, signal?: AbortSignal}) => Promise<any>, createGroup: (imageUid: string, options?: {signal?: AbortSignal}) => Promise<any>}} SourceApi */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */

/** Own source selection, pagination and initial Candidate-group reservation. */
export class CardSourceBrowser {
  /** @param {{root: HTMLElement, api: SourceApi, requests: RequestBoundary, locationRef?: Location, pageSize?: number}} dependencies */
  constructor(dependencies) {
    this.root = dependencies.root;
    this.api = dependencies.api;
    this.requests = dependencies.requests;
    this.locationRef = dependencies.locationRef || window.location;
    this.pageSize = dependencies.pageSize || 24;
    this.offset = 0;
    this.total = 0;
    this.abortController = new AbortController();
    this.grid = requiredElement(this.root, "[data-card-source-grid]");
    this.status = requiredElement(this.root, "[data-card-factory-status]");
    this.page = requiredElement(this.root, "[data-source-page]");
    this.previous = requiredButton(this.root, "[data-source-previous]");
    this.next = requiredButton(this.root, "[data-source-next]");
  }

  /** Bind controls and load the first canonical source page. */
  async start() {
    this.previous.addEventListener("click", () => void this.#move(-1), {
      signal: this.abortController.signal,
    });
    this.next.addEventListener("click", () => void this.#move(1), {
      signal: this.abortController.signal,
    });
    await this.reload();
  }

  /** Reload current sources through the shared request lifecycle. */
  async reload() {
    this.requests.cancelRequests();
    this.status.textContent = "Quellen werden geladen …";
    try {
      const result = await this.requests.run((signal) =>
        this.api.sources({
          offset: this.offset,
          limit: this.pageSize,
          signal,
        }),
      );
      this.total = Number(result.total || 0);
      this.#render(Array.isArray(result.items) ? result.items : []);
      this.status.textContent = `${this.total} geeignete Quellbilder`;
    } catch (error) {
      if (!isAbortError(error)) {
        this.grid.replaceChildren(
          message("card-error-state", errorMessage(error)),
        );
        this.status.textContent = "Quellen konnten nicht geladen werden";
      }
    }
  }

  /** Dispose all listeners and in-flight work. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
  }

  /** @param {number} direction */
  async #move(direction) {
    this.offset = Math.max(0, this.offset + direction * this.pageSize);
    await this.reload();
  }

  /** @param {Array<Record<string, any>>} items */
  #render(items) {
    if (!items.length) {
      this.grid.replaceChildren(
        message(
          "card-empty-state",
          "Keine zugänglichen STANDARD-Bilder gefunden.",
        ),
      );
    } else {
      this.grid.replaceChildren(...items.map((item) => this.#source(item)));
    }
    const first = this.total ? this.offset + 1 : 0;
    const last = Math.min(this.offset + this.pageSize, this.total);
    this.page.textContent = `${first}–${last} von ${this.total}`;
    this.previous.disabled = this.offset === 0;
    this.next.disabled = this.offset + this.pageSize >= this.total;
  }

  /** @param {Record<string, any>} item */
  #source(item) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "card-source-item";
    const image = document.createElement("img");
    image.src = String(item.image_url || "");
    image.alt = "Card-Quellbild";
    image.loading = "lazy";
    const label = document.createElement("span");
    label.textContent = String(item.image_uid || "Unbekannte Bild-UID");
    button.append(image, label);
    button.addEventListener(
      "click",
      () => void this.#create(String(item.image_uid || ""), button),
      { signal: this.abortController.signal },
    );
    return button;
  }

  /** @param {string} imageUid @param {HTMLButtonElement} button */
  async #create(imageUid, button) {
    button.disabled = true;
    this.status.textContent = "Bild wird analysiert und Karte erstellt …";
    try {
      await this.requests.run((signal) =>
        this.api.createGroup(imageUid, { signal }),
      );
      this.locationRef.assign("/card-candidate-groups");
    } catch (error) {
      if (!isAbortError(error)) this.status.textContent = errorMessage(error);
      button.disabled = false;
    }
  }
}

/** @param {ParentNode} root @param {string} selector */
function requiredElement(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLElement)) throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {ParentNode} root @param {string} selector */
function requiredButton(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLButtonElement))
    throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {string} className @param {string} text */
function message(className, text) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  paragraph.textContent = text;
  return paragraph;
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
