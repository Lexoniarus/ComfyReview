import { CardFactoryApi } from "../card-factory/card-factory-api.js";
import { CardDeckController } from "../card-factory/deck-controller.js";
import { CardDeckView } from "../card-factory/deck-view.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";

const root = document.querySelector("[data-card-deck]");
if (root instanceof HTMLElement) {
  const controller = new CardDeckController({
    api: new CardFactoryApi(new ApiClient("/api/v2")),
    view: new CardDeckView(root, {
      onAdd: (cardId) => void controller.add(cardId),
      onRemove: (cardId) => void controller.remove(cardId),
      onMove: (cardId, direction) => void controller.move(cardId, direction),
      onDevelop: (cardId) => void controller.develop(cardId),
    }),
    requests: new RequestLifecycle(),
  });
  void controller.start();
  window.addEventListener("pagehide", () => controller.dispose(), {
    once: true,
  });
}
