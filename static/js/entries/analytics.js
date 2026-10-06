import { AnalyticsView } from "../analytics/focused-analytics-view.js";
import { AnalyticsCollectionController } from "../analytics/analytics-collection-controller.js";
import { PlaygroundIntentTray } from "../analytics/playground-intent-tray.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { PlaygroundIntentStore } from "../playground/playground-intent.js";
import { AnalyticsController } from "../surfaces/focused-analytics-controller.js";

const root = document.querySelector('[data-v2-surface="analytics"]');
if (root instanceof HTMLElement) {
  const form = root.querySelector("[data-analytics-filters]");
  const model = root.querySelector("[data-analytics-model]");
  const minimumSamples = root.querySelector("[data-analytics-minimum]");
  const report = root.querySelector("[data-analytics-report]");
  const status = root.querySelector("[data-analytics-status]");
  const trayRoot = root.querySelector("[data-analytics-intent-tray]");
  const toastRoot = root.querySelector("[data-analytics-toast]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  if (
    form instanceof HTMLFormElement &&
    model instanceof HTMLInputElement &&
    minimumSamples instanceof HTMLInputElement &&
    report instanceof HTMLElement &&
    status instanceof HTMLElement &&
    trayRoot instanceof HTMLElement &&
    toastRoot instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement
  ) {
    const viewer = new ImageViewer(viewerRoot);
    const api = new ApiClient();
    const intentStore = new PlaygroundIntentStore(window.sessionStorage);
    const generatorActions = new ImageGeneratorActions({
      api,
      store: intentStore,
    });
    const tray = new PlaygroundIntentTray(
      trayRoot,
      toastRoot,
      intentStore,
      window.location,
    );
    const controller = new AnalyticsController({
      section: root.dataset.section || "overview",
      api,
      requests: new RequestLifecycle(),
      detailRequests: new RequestLifecycle(),
      collection: new AnalyticsCollectionController({
        requests: new RequestLifecycle(),
        status,
      }),
      intentNavigator: { open: (element) => tray.stage(element) },
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
        tray.dispose();
        generatorActions.dispose();
        viewer.dispose();
      },
      {
        once: true,
      },
    );
  }
}
