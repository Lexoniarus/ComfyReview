import { CardFactoryApi } from "../card-factory/card-factory-api.js";
import { CardWorkshopController } from "../card-factory/workshop-controller.js";
import { CardWorkshopView } from "../card-factory/workshop-view.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";

const root = document.querySelector("[data-card-workshop]");
if (root instanceof HTMLElement) {
  const sessionId = String(root.dataset.sessionId || "");
  /** @type {CardWorkshopController | null} */
  let controller = null;
  const view = new CardWorkshopView(root, {
    onAccept: (candidateId) => void controller?.accept(candidateId),
  });
  controller = new CardWorkshopController({
    sessionId,
    api: new CardFactoryApi(new ApiClient("/api/v2")),
    view,
    requests: new RequestLifecycle(),
  });
  void controller.start();
  window.addEventListener("pagehide", () => controller?.dispose(), {
    once: true,
  });
}
