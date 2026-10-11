import { CardFactoryApi } from "../card-factory/card-factory-api.js";
import { CardCandidateGroupOverview } from "../card-factory/group-overview.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";

const root = document.querySelector("[data-card-candidate-groups]");
if (root instanceof HTMLElement) {
  const overview = new CardCandidateGroupOverview({
    root,
    api: new CardFactoryApi(new ApiClient("/api/v2")),
    requests: new RequestLifecycle(),
  });
  void overview.start();
  window.addEventListener("pagehide", () => overview.dispose(), { once: true });
}
