import { describe, expect, it, vi } from "vitest";

import { CardFactoryApi } from "../../static/js/card-factory/card-factory-api.js";

describe("CardFactoryApi", () => {
  it("maps complete group, pool, development and deck operations", async () => {
    const client = {
      get: vi.fn(() => Promise.resolve({})),
      post: vi.fn(() => Promise.resolve({})),
      put: vi.fn(() => Promise.resolve({})),
      delete: vi.fn(() => Promise.resolve({})),
    };
    const api = new CardFactoryApi(client);
    const signal = new AbortController().signal;

    await api.sources({ offset: 24, limit: 12, signal });
    await api.createGroup("image 1", { signal });
    await api.groups({ signal });
    await api.group("group 1", { signal });
    await api.rejectGroup("group 1", 2, { signal });
    await api.retryGroup("group 1", 2, { signal });
    await api.acceptCandidate("group 1", "candidate 1", 2, { signal });
    await api.cards({ signal });
    await api.card("card 1", { signal });
    await api.develop("card 1", 3, { signal });
    await api.deck({ signal });
    await api.addDeckCard("card 1", 4, { signal });
    await api.removeDeckCard("card 1", 5, { signal });
    await api.reorderDeck(["card 2", "card 1"], 6, { signal });

    expect(client.get).toHaveBeenCalledWith(
      "card-factory/sources?offset=24&limit=12",
      { signal },
    );
    expect(client.get).toHaveBeenCalledWith(
      "card-factory/candidate-groups/group%201",
      { signal },
    );
    expect(client.post).toHaveBeenCalledWith(
      "card-factory/candidate-groups",
      { image_uid: "image 1" },
      { signal },
    );
    expect(client.post).toHaveBeenCalledWith(
      "card-factory/candidate-groups/group%201/candidates/candidate%201/accept",
      { expected_revision: 2 },
      { signal },
    );
    expect(client.post).toHaveBeenCalledWith(
      "card-factory/cards/card%201/development-groups",
      { expected_revision: 3 },
      { signal },
    );
    expect(client.delete).toHaveBeenCalledWith(
      "card-factory/deck/cards/card%201",
      { expected_revision: 5 },
      { signal },
    );
    expect(client.put).toHaveBeenCalledWith(
      "card-factory/deck/order",
      { expected_revision: 6, card_ids: ["card 2", "card 1"] },
      { signal },
    );
  });
});
