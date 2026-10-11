/** @typedef {{deck: (options?: {signal?: AbortSignal}) => Promise<any>, addDeckCard: (cardId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, removeDeckCard: (cardId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, reorderDeck: (cardIds: Array<string>, revision: number, options?: {signal?: AbortSignal}) => Promise<any>, develop: (cardId: string, revision: number, options?: {signal?: AbortSignal}) => Promise<any>}} DeckApi */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, dispose: () => void}} RequestBoundary */
/** @typedef {{deck: {revision: number, entries: Array<{card_id: string}>}, pool: Array<{card_id: string, revision: number}>}} DeckPayload */

/** Own revision-safe deck mutations and Card development navigation. */
export class CardDeckController {
  /** @param {{api: DeckApi, view: any, requests: RequestBoundary, locationRef?: Location}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.view = dependencies.view;
    this.requests = dependencies.requests;
    this.locationRef = dependencies.locationRef || window.location;
    /** @type {DeckPayload|null} */
    this.payload = null;
  }

  /** Load the current pool and deck aggregate. */
  async start() {
    try {
      this.payload = await this.requests.run((signal) =>
        this.api.deck({ signal }),
      );
      this.view.render(this.payload);
    } catch (error) {
      this.view.showError(errorMessage(error));
    }
  }

  /** @param {string} cardId */
  async add(cardId) {
    await this.#deckMutation((revision, signal) =>
      this.api.addDeckCard(cardId, revision, { signal }),
    );
  }

  /** @param {string} cardId */
  async remove(cardId) {
    await this.#deckMutation((revision, signal) =>
      this.api.removeDeckCard(cardId, revision, { signal }),
    );
  }

  /** @param {string} cardId @param {number} direction */
  async move(cardId, direction) {
    if (!this.payload) return;
    const ids = this.payload.deck.entries.map((entry) => String(entry.card_id));
    const current = ids.indexOf(cardId);
    const target = current + direction;
    if (current < 0 || target < 0 || target >= ids.length) return;
    [ids[current], ids[target]] = [ids[target], ids[current]];
    await this.#deckMutation((revision, signal) =>
      this.api.reorderDeck(ids, revision, { signal }),
    );
  }

  /** @param {string} cardId */
  async develop(cardId) {
    if (!this.payload) return;
    const card = this.payload.pool.find((item) => item.card_id === cardId);
    if (!card) return;
    this.view.setBusy(true);
    try {
      const group = await this.requests.run((signal) =>
        this.api.develop(cardId, Number(card.revision), { signal }),
      );
      this.locationRef.assign(
        `/card-candidate-groups/${encodeURIComponent(String(group.group_id))}`,
      );
    } catch (error) {
      this.view.showError(errorMessage(error));
    } finally {
      this.view.setBusy(false);
    }
  }

  dispose() {
    this.requests.dispose();
    this.view.dispose();
  }

  /** @param {(revision: number, signal: AbortSignal) => Promise<any>} operation */
  async #deckMutation(operation) {
    const currentPayload = this.payload;
    if (!currentPayload) return;
    this.view.setBusy(true);
    try {
      const deck = await this.requests.run((signal) =>
        operation(Number(currentPayload.deck.revision), signal),
      );
      this.payload = { ...currentPayload, deck };
      this.view.render(this.payload);
    } catch (error) {
      this.view.showError(errorMessage(error));
    } finally {
      this.view.setBusy(false);
    }
  }
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
