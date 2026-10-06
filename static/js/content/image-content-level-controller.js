/** @typedef {{put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{setContentLevelBusy: (busy: boolean) => void, showContentLevelError: (message: string) => void}} InspectorBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{confirm: (message: string) => Promise<boolean>, dispose: () => void}} DialogBoundary */
/** Coordinate audited image-level overrides through the shared API boundary. */
export class ImageContentLevelController {
  /** @param {{api: ApiBoundary, inspector: InspectorBoundary, requests: RequestBoundary, dialog: DialogBoundary, onChanged: (imageUid: string) => Promise<void>, onDeleted: () => Promise<void>}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.inspector = dependencies.inspector;
    this.requests = dependencies.requests;
    this.dialog = dependencies.dialog;
    this.onChanged = dependencies.onChanged;
    this.onDeleted = dependencies.onDeleted;
    this.isMutating = false;
  }

  /** @param {string} imageUid @param {string | null} contentLevel */
  async assign(imageUid, contentLevel) {
    if (this.isMutating) return;
    this.isMutating = true;
    this.inspector.setContentLevelBusy(true);
    this.inspector.showContentLevelError("");
    try {
      await this.requests.run((/** @type {AbortSignal} */ signal) =>
        this.api.put(
          `images/${encodeURIComponent(imageUid)}/content-level`,
          { content_level: contentLevel },
          { signal },
        ),
      );
      await this.onChanged(imageUid);
    } catch (error) {
      if (!isAbortError(error)) {
        this.inspector.showContentLevelError(errorMessage(error));
      }
    } finally {
      this.isMutating = false;
      this.inspector.setContentLevelBusy(false);
    }
  }

  /** @param {string} imageUid */
  async delete(imageUid) {
    if (this.isMutating) return;
    const confirmed = await this.dialog.confirm(
      "Das Bild wird über den bestehenden kanonischen Löschpfad entfernt.",
    );
    if (!confirmed) return;
    this.isMutating = true;
    this.inspector.setContentLevelBusy(true);
    try {
      await this.requests.run((/** @type {AbortSignal} */ signal) =>
        this.api.post(
          `images/${encodeURIComponent(imageUid)}/delete`,
          {},
          { signal },
        ),
      );
      await this.onDeleted();
    } catch (error) {
      if (!isAbortError(error)) {
        this.inspector.showContentLevelError(errorMessage(error));
      }
    } finally {
      this.isMutating = false;
      this.inspector.setContentLevelBusy(false);
    }
  }

  dispose() {
    this.requests.dispose();
    this.dialog.dispose();
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
    : "Die Inhaltsstufe konnte nicht geändert werden.";
}
