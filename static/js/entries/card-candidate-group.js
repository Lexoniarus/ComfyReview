import { CardFactoryApi } from "../card-factory/card-factory-api.js";
import { CardCandidateGroupComparisonController } from "../card-factory/group-comparison-controller.js";
import { CardCandidateGroupComparisonView } from "../card-factory/group-comparison-view.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";

const root = document.querySelector("[data-card-candidate-group]");
if (root instanceof HTMLElement) {
  const controller = new CardCandidateGroupComparisonController({
    groupId: String(root.dataset.groupId || ""),
    api: new CardFactoryApi(new ApiClient("/api/v2")),
    view: new CardCandidateGroupComparisonView(root, {
      onAccept: (candidateId) => void controller.accept(candidateId),
    }),
    requests: new RequestLifecycle(),
  });
  void controller.start();
  window.addEventListener("pagehide", () => controller.dispose(), {
    once: true,
  });
}
