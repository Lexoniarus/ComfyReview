/** @typedef {{get: (path: string, options: {signal?: AbortSignal}) => Promise<any>, put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{setCurationOptions: (setKeys: string[]) => void, setCurationBusy: (busy: boolean) => void, showCurationError: (message: string) => void}} InspectorBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{api: ApiBoundary, inspector: InspectorBoundary, requests: RequestBoundary, onAssigned: (imageUid: string) => Promise<void>}} CurationDependencies */

/** Coordinate canonical curation choices and UID-only assignments. */
export class ImageCurationController {
  /** @param {CurationDependencies} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.inspector = dependencies.inspector;
    this.requests = dependencies.requests;
    this.onAssigned = dependencies.onAssigned;
    this.isMutating = false;
    this.isDisposed = false;
  }

  /** Load the server-authoritative list of curation sets. */
  async start() {
    if (this.isDisposed) return;
    try {
      const payload = await this.requests.run((signal) =>
        this.api.get("curation/sets", { signal }),
      );
      this.inspector.setCurationOptions(payload.set_keys || []);
    } catch (error) {
      if (!isAbortError(error)) {
        this.inspector.showCurationError(errorMessage(error));
      }
    }
  }

  /** @param {string} imageUid @param {string} setKey */
  async assign(imageUid, setKey) {
    if (this.isDisposed || this.isMutating) return;
    this.isMutating = true;
    this.inspector.showCurationError("");
    this.inspector.setCurationBusy(true);
    try {
      await this.requests.run((signal) =>
        this.api.put(
          `images/${encodeURIComponent(imageUid)}/curation`,
          { set_key: setKey },
          { signal },
        ),
      );
      await this.onAssigned(imageUid);
    } catch (error) {
      if (!isAbortError(error)) {
        this.inspector.showCurationError(errorMessage(error));
      }
    } finally {
      this.isMutating = false;
      this.inspector.setCurationBusy(false);
    }
  }

  /** Release the controller's request owner. */
  dispose() {
    if (this.isDisposed) return;
    this.isDisposed = true;
    this.requests.dispose();
  }
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
