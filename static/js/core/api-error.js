/** Normalize one failed API request for browser controllers. */
export class ApiError extends Error {
  /**
   * @param {object} options
   * @param {string} options.code
   * @param {string} options.message
   * @param {number} options.status
   * @param {string | null} options.traceId
   */
  constructor({ code, message, status, traceId }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.traceId = traceId;
  }
}
