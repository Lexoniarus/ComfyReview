/** @typedef {{get: (path: string, options: {signal?: AbortSignal}) => Promise<any>}} ApiBoundary */
/** @typedef {{render: (image: any) => void, renderReviews: (events: any[]) => void, reviewsLoading: () => void, reviewsError: (message: string) => void, loading: () => void, empty: () => void, error: (message: string) => void, dispose: () => void}} InspectorViewBoundary */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} RequestBoundary */

/** Coordinate image presentation with its separately loaded review history. */
export class ImageInspectorController {
  /** @param {{api: ApiBoundary, view: InspectorViewBoundary, requests: RequestBoundary}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.view = dependencies.view;
    this.requests = dependencies.requests;
    this.currentImageUid = "";
  }

  /** @param {Record<string, any>} image */
  render(image) {
    this.requests.cancelRequests();
    this.currentImageUid = String(image.image_uid || "");
    this.view.render(image);
    this.view.reviewsLoading();
    if (this.currentImageUid) void this.#loadReviews(this.currentImageUid);
  }

  /** Show the image-context loading state and cancel stale history. */
  loading() {
    this.#clearHistoryRequest();
    this.view.loading();
  }

  /** Show the neutral state and cancel stale history. */
  empty() {
    this.#clearHistoryRequest();
    this.view.empty();
  }

  /** @param {string} message */
  error(message) {
    this.#clearHistoryRequest();
    this.view.error(message);
  }

  /** Release review-history requests and the inspector view. */
  dispose() {
    this.currentImageUid = "";
    this.requests.dispose();
    this.view.dispose();
  }

  /** @param {string} imageUid */
  async #loadReviews(imageUid) {
    try {
      const payload = await this.requests.run((signal) =>
        this.api.get(`images/${encodeURIComponent(imageUid)}/reviews`, {
          signal,
        }),
      );
      if (this.currentImageUid === imageUid) {
        this.view.renderReviews(payload.events || []);
      }
    } catch (error) {
      if (!isAbortError(error) && this.currentImageUid === imageUid) {
        this.view.reviewsError(errorMessage(error));
      }
    }
  }

  #clearHistoryRequest() {
    this.currentImageUid = "";
    this.requests.cancelRequests();
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
    : "Bewertungshistorie konnte nicht geladen werden.";
}
