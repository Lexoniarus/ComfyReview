/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiClientBoundary */

/** Typed Card Factory API facade over the shared frontend client. */
export class CardFactoryApi {
  /** @param {ApiClientBoundary} client */
  constructor(client) {
    this.client = client;
  }

  /** @param {{offset: number, limit: number, signal?: AbortSignal}} options */
  sources(options) {
    const query = new URLSearchParams({
      offset: String(options.offset),
      limit: String(options.limit),
    });
    return this.client.get(`card-factory/sources?${query.toString()}`, {
      signal: options.signal,
    });
  }

  /** @param {string} imageUid @param {{signal?: AbortSignal}} [options] */
  create(imageUid, options = {}) {
    return this.client.post(
      "card-factory/sessions",
      { image_uid: imageUid },
      options,
    );
  }

  /** @param {string} sessionId @param {{signal?: AbortSignal}} [options] */
  session(sessionId, options = {}) {
    return this.client.get(
      `card-factory/sessions/${encodeURIComponent(sessionId)}`,
      options,
    );
  }

  /** @param {string} sessionId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  generate(sessionId, revision, options = {}) {
    return this.client.post(
      `card-factory/sessions/${encodeURIComponent(sessionId)}/candidates`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {string} sessionId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  develop(sessionId, revision, options = {}) {
    return this.client.post(
      `card-factory/sessions/${encodeURIComponent(sessionId)}/develop`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {string} sessionId @param {string} candidateId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  accept(sessionId, candidateId, revision, options = {}) {
    return this.client.post(
      `card-factory/sessions/${encodeURIComponent(sessionId)}/candidates/${encodeURIComponent(candidateId)}/accept`,
      { expected_revision: revision },
      options,
    );
  }
}
