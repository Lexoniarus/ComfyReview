import { beforeEach, describe, expect, it, vi } from "vitest";

import { CardDeckController } from "../../static/js/card-factory/deck-controller.js";
import { CardDeckView } from "../../static/js/card-factory/deck-view.js";

describe("Card pool and deck", () => {
  beforeEach(() => {
    document.body.innerHTML = markup();
  });

  it("renders pool and ordered deck with explicit development actions", () => {
    const actions = {
      onAdd: vi.fn(),
      onRemove: vi.fn(),
      onMove: vi.fn(),
      onDevelop: vi.fn(),
    };
    const view = new CardDeckView(document.querySelector("main"), actions);

    view.render(payload());

    expect(
      document.querySelectorAll("[data-deck-list] .pool-card"),
    ).toHaveLength(1);
    expect(
      document.querySelectorAll("[data-card-pool] .pool-card"),
    ).toHaveLength(2);
    expect(document.querySelector("[data-deck-capacity]").textContent).toBe(
      "1 / 40",
    );
    const poolButtons = document.querySelectorAll(
      "[data-card-pool] .pool-card:last-child button",
    );
    poolButtons[0].click();
    poolButtons[1].click();
    expect(actions.onAdd).toHaveBeenCalledWith("card-2");
    expect(actions.onDevelop).toHaveBeenCalledWith("card-2");
  });

  it("uses current revisions for add remove reorder and development", async () => {
    const current = payload();
    const deckAfterAdd = {
      ...current.deck,
      revision: 4,
      entries: [
        ...current.deck.entries,
        { card_id: "card-2", position: 1, card: current.pool[1] },
      ],
    };
    const api = {
      deck: vi.fn(() => Promise.resolve(current)),
      addDeckCard: vi.fn(() => Promise.resolve(deckAfterAdd)),
      removeDeckCard: vi.fn(() => Promise.resolve(current.deck)),
      reorderDeck: vi.fn(() => Promise.resolve(deckAfterAdd)),
      develop: vi.fn(() => Promise.resolve({ group_id: "development-1" })),
    };
    const view = {
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const requests = requestFixture();
    const locationRef = { assign: vi.fn() };
    const controller = new CardDeckController({
      api,
      view,
      requests,
      locationRef,
    });

    await controller.start();
    await controller.add("card-2");
    await controller.move("card-2", -1);
    await controller.remove("card-2");
    await controller.develop("card-1");

    expect(api.addDeckCard).toHaveBeenCalledWith(
      "card-2",
      3,
      expect.any(Object),
    );
    expect(api.reorderDeck).toHaveBeenCalledWith(
      ["card-2", "card-1"],
      4,
      expect.any(Object),
    );
    expect(api.develop).toHaveBeenCalledWith("card-1", 2, expect.any(Object));
    expect(locationRef.assign).toHaveBeenCalledWith(
      "/card-candidate-groups/development-1",
    );
    controller.dispose();
    expect(requests.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces load and mutation failures", async () => {
    const api = {
      deck: vi.fn(() => Promise.reject(new Error("load failed"))),
    };
    const view = {
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new CardDeckController({
      api,
      view,
      requests: requestFixture(),
    });

    await controller.start();

    expect(view.showError).toHaveBeenCalledWith("load failed");
  });
});

function payload() {
  const cards = [card("card-1", 2), card("card-2", 1)];
  return {
    deck: {
      deck_id: "poc-deck",
      revision: 3,
      capacity: 40,
      remaining_capacity: 39,
      entries: [{ card_id: "card-1", position: 0, card: cards[0] }],
    },
    pool: cards,
  };
}

function card(cardId, revision) {
  return {
    card_id: cardId,
    revision,
    card_spec: {
      rarity_key: "common",
      level: 1,
      stats: { attack: 100, defense: 200 },
    },
    presentation: { presentation: { card_title: `Karte ${cardId}` } },
    active_image: { image_url: `/${cardId}.png` },
    actions: { can_develop: true },
  };
}

function markup() {
  return `<main data-card-deck>
    <span data-deck-status></span><span data-deck-capacity></span>
    <section data-deck-list></section><section data-card-pool></section>
  </main>`;
}

function requestFixture() {
  return {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    dispose: vi.fn(),
  };
}
