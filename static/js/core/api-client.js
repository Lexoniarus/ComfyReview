import { ApiError } from "./api-error.js";

/** Own all browser HTTP access to the JSON API. */
export class ApiClient {
  /** @param {string} [baseUrl] */
  constructor(baseUrl = "/api/v2") {
    this.baseUrl = baseUrl.replace(/\/$/u, "");
  }

  /** @param {string} path @param {{signal?: AbortSignal, keepalive?: boolean}} [options] */
  get(path, options = {}) {
    return this.#request("GET", path, undefined, options);
  }

  /**
   * @param {string} path
   * @param {unknown} body
   * @param {{signal?: AbortSignal, keepalive?: boolean}} [options]
   */
  post(path, body, options = {}) {
    return this.#request("POST", path, body, options);
  }

  /**
   * @param {string} path
   * @param {unknown} body
   * @param {{signal?: AbortSignal, keepalive?: boolean}} [options]
   */
  put(path, body, options = {}) {
    return this.#request("PUT", path, body, options);
  }

  /**
   * @param {string} path
   * @param {unknown} body
   * @param {{signal?: AbortSignal, keepalive?: boolean}} [options]
   */
  patch(path, body, options = {}) {
    return this.#request("PATCH", path, body, options);
  }

  /**
   * @param {string} method
   * @param {string} path
   * @param {unknown} body
   * @param {{signal?: AbortSignal, keepalive?: boolean}} options
   */
  async #request(method, path, body, options) {
    const requestHeaders = new Headers({ Accept: "application/json" });
    /** @type {RequestInit} */
    const request = {
      headers: requestHeaders,
      method,
      signal: options.signal,
      keepalive: Boolean(options.keepalive),
    };
    if (body !== undefined) {
      requestHeaders.set("Content-Type", "application/json");
      request.body = JSON.stringify(body);
    }
    const response = await fetch(this.#url(path), request);
    if (response.status === 204) {
      return null;
    }
    const payload = await this.#json(response);
    if (!response.ok) {
      throw this.#error(response, payload);
    }
    return payload;
  }

  /** @param {string} path */
  #url(path) {
    const suffix = String(path || "").replace(/^\/+/, "");
    return `${this.baseUrl}/${suffix}`;
  }

  /** @param {Response} response */
  async #json(response) {
    try {
      return await response.json();
    } catch {
      throw new ApiError({
        code: "invalid_response",
        message: "Die API-Antwort war nicht lesbar.",
        status: response.status,
        traceId: response.headers.get("x-request-id"),
      });
    }
  }

  /** @param {Response} response @param {unknown} payload */
  #error(response, payload) {
    const candidate =
      payload && typeof payload === "object" && "error" in payload
        ? payload.error
        : null;
    const details = candidate && typeof candidate === "object" ? candidate : {};
    return new ApiError({
      code:
        "code" in details && typeof details.code === "string"
          ? details.code
          : "request_failed",
      message:
        "message" in details && typeof details.message === "string"
          ? details.message
          : "Die Anfrage ist fehlgeschlagen.",
      status: response.status,
      traceId:
        "trace_id" in details && typeof details.trace_id === "string"
          ? details.trace_id
          : response.headers.get("x-request-id"),
    });
  }
}
