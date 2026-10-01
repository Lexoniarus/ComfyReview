import { AnalyticsView } from "../analytics/analytics-view.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { AnalyticsController } from "../surfaces/analytics-controller.js";

const root = document.querySelector('[data-v2-surface="analytics"]');
if (root instanceof HTMLElement) {
  const form = root.querySelector("[data-analytics-filters]");
  const model = root.querySelector("[data-analytics-model]");
  const minimumSamples = root.querySelector("[data-analytics-minimum]");
  const scope = root.querySelector("[data-analytics-scope]");
  const report = root.querySelector("[data-analytics-report]");
  const status = root.querySelector("[data-analytics-status]");
  if (
    form instanceof HTMLFormElement &&
    model instanceof HTMLInputElement &&
    minimumSamples instanceof HTMLInputElement &&
    scope instanceof HTMLSelectElement &&
    report instanceof HTMLElement &&
    status instanceof HTMLElement
  ) {
    const controller = new AnalyticsController({
      section: root.dataset.section || "overview",
      api: new ApiClient(),
      requests: new RequestLifecycle(),
      view: new AnalyticsView(report),
      form,
      model,
      minimumSamples,
      scope,
      status,
    });
    void controller.start();
    window.addEventListener("pagehide", () => controller.dispose(), {
      once: true,
    });
  }
}
