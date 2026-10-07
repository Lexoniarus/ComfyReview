import { AnalyticsView } from "../analytics/focused-analytics-view.js";
import { AnalyticsCollectionController } from "../analytics/analytics-collection-controller.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { GeneratorHandoffNavigator } from "../playground/playground-intent.js";
import { AnalyticsController } from "../surfaces/focused-analytics-controller.js";

const root = document.querySelector('[data-v2-surface="analytics"]');
if (root instanceof HTMLElement) {
  const form = root.querySelector("[data-analytics-filters]");
  const model = root.querySelector("[data-analytics-model]");
  const minimumSamples = root.querySelector("[data-analytics-minimum]");
  const report = root.querySelector("[data-analytics-report]");
  const status = root.querySelector("[data-analytics-status]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  if (
    form instanceof HTMLFormElement &&
    model instanceof HTMLInputElement &&
    minimumSamples instanceof HTMLInputElement &&
    report instanceof HTMLElement &&
    status instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement
  ) {
    const viewer = new ImageViewer(viewerRoot);
    const api = new ApiClient();
    const handoffNavigator = new GeneratorHandoffNavigator(window.location);
    const generatorActions = new ImageGeneratorActions(handoffNavigator);
    const controller = new AnalyticsController({
      section: root.dataset.section || "overview",
      api,
      requests: new RequestLifecycle(),
      detailRequests: new RequestLifecycle(),
      collection: new AnalyticsCollectionController({
        requests: new RequestLifecycle(),
        status,
      }),
      intentNavigator: handoffNavigator,
      view: new AnalyticsView(report, {
        onImageSelect: (
          /** @type {string} */ _imageUid,
          /** @type {string} */ imageUrl,
        ) => viewer.open(imageUrl),
        createGeneratorActions: (imageUid) => generatorActions.create(imageUid),
      }),
      form,
      model,
      minimumSamples,
      report,
      status,
    });
    void controller.start();
    window.addEventListener(
      "pagehide",
      () => {
        controller.dispose();
        generatorActions.dispose();
        viewer.dispose();
      },
      {
        once: true,
      },
    );
  }
}
