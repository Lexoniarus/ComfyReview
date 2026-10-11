import { CardFactoryApi } from "../card-factory/card-factory-api.js";
import { CardSourceBrowser } from "../card-factory/source-browser.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";

const root = document.querySelector("[data-card-factory-sources]");
if (root instanceof HTMLElement) {
  const browser = new CardSourceBrowser({
    root,
    api: new CardFactoryApi(new ApiClient("/api/v2")),
    requests: new RequestLifecycle(),
  });
  void browser.start();
  window.addEventListener("pagehide", () => browser.dispose(), { once: true });
}
