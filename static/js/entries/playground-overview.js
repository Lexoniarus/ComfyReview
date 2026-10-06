import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { PlaygroundIntentNavigator } from "../playground/playground-intent.js";
import { PlaygroundIntentStore } from "../playground/playground-intent.js";
import { TopCombinationsView } from "../playground/top-combinations.js";

const root = document.querySelector("[data-v2-surface='playground-overview']");
if (root instanceof HTMLElement) {
  const combinations = root.querySelector("[data-top-combinations]");
  const status = root.querySelector("[data-playground-status]");
  if (combinations instanceof HTMLElement && status instanceof HTMLElement) {
    const requests = new RequestLifecycle();
    const api = new ApiClient();
    const intentStore = new PlaygroundIntentStore(window.sessionStorage);
    const generatorActions = new ImageGeneratorActions({
      api,
      store: intentStore,
    });
    const view = new TopCombinationsView(
      combinations,
      new PlaygroundIntentNavigator(window.location, intentStore),
      {
        createGeneratorActions: (imageUid) => generatorActions.create(imageUid),
      },
    );
    requests
      .run((signal) => api.get("playground/top-combinations", { signal }))
      .then((payload) => {
        view.render(payload);
        status.textContent = "";
      })
      .catch((error) => {
        status.textContent =
          error instanceof Error ? error.message : "Laden fehlgeschlagen.";
      });
    window.addEventListener(
      "pagehide",
      () => {
        requests.dispose();
        view.dispose();
        generatorActions.dispose();
      },
      { once: true },
    );
  }
}
