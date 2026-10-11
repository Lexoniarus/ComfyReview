/** @typedef {{get: (path: string, options?: {signal?: AbortSignal}) => Promise<any>, post: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, put: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>, delete: (path: string, body: unknown, options?: {signal?: AbortSignal}) => Promise<any>}} ApiClientBoundary */

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
  createGroup(imageUid, options = {}) {
    return this.client.post(
      "card-factory/candidate-groups",
      { image_uid: imageUid },
      options,
    );
  }

  /** @param {{signal?: AbortSignal}} [options] */
  groups(options = {}) {
    return this.client.get("card-factory/candidate-groups", options);
  }

  /** @param {string} groupId @param {{signal?: AbortSignal}} [options] */
  group(groupId, options = {}) {
    return this.client.get(
      `card-factory/candidate-groups/${encodeURIComponent(groupId)}`,
      options,
    );
  }

  /** @param {string} groupId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  rejectGroup(groupId, revision, options = {}) {
    return this.client.post(
      `card-factory/candidate-groups/${encodeURIComponent(groupId)}/reject`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {string} groupId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  retryGroup(groupId, revision, options = {}) {
    return this.client.post(
      `card-factory/candidate-groups/${encodeURIComponent(groupId)}/retry`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {string} groupId @param {string} candidateId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  acceptCandidate(groupId, candidateId, revision, options = {}) {
    return this.client.post(
      `card-factory/candidate-groups/${encodeURIComponent(groupId)}/candidates/${encodeURIComponent(candidateId)}/accept`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {{signal?: AbortSignal}} [options] */
  cards(options = {}) {
    return this.client.get("card-factory/cards", options);
  }

  /** @param {string} cardId @param {{signal?: AbortSignal}} [options] */
  card(cardId, options = {}) {
    return this.client.get(
      `card-factory/cards/${encodeURIComponent(cardId)}`,
      options,
    );
  }

  /** @param {string} cardId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  develop(cardId, revision, options = {}) {
    return this.client.post(
      `card-factory/cards/${encodeURIComponent(cardId)}/development-groups`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {{signal?: AbortSignal}} [options] */
  deck(options = {}) {
    return this.client.get("card-factory/deck", options);
  }

  /** @param {string} cardId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  addDeckCard(cardId, revision, options = {}) {
    return this.client.post(
      `card-factory/deck/cards/${encodeURIComponent(cardId)}`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {string} cardId @param {number} revision @param {{signal?: AbortSignal}} [options] */
  removeDeckCard(cardId, revision, options = {}) {
    return this.client.delete(
      `card-factory/deck/cards/${encodeURIComponent(cardId)}`,
      { expected_revision: revision },
      options,
    );
  }

  /** @param {Array<string>} cardIds @param {number} revision @param {{signal?: AbortSignal}} [options] */
  reorderDeck(cardIds, revision, options = {}) {
    return this.client.put(
      "card-factory/deck/order",
      { expected_revision: revision, card_ids: cardIds },
      options,
    );
  }
}
