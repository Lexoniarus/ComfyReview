import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { GenerationDetail } from "../generations/generation-detail.js";
import { GenerationList } from "../generations/generation-list.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { GeneratorHandoffNavigator } from "../playground/playground-intent.js";
import { GenerationsController } from "../surfaces/generations-controller.js";

const root = document.querySelector("[data-v2-surface='generations']");
if (root) {
  const listRoot = root.querySelector("[data-generation-list]");
  const detailRoot = root.querySelector("[data-generation-detail]");
  const statusFilter = root.querySelector("[data-generation-status-filter]");
  const status = root.querySelector("[data-generation-status]");
  if (
    !(listRoot instanceof HTMLElement) ||
    !(detailRoot instanceof HTMLElement) ||
    !(statusFilter instanceof HTMLSelectElement) ||
    !(status instanceof HTMLElement)
  ) {
    throw new Error("Generations V2 shell is incomplete");
  }
  /** @type {GenerationsController | null} */
  let controller = null;
  const api = new ApiClient("/api/v2");
  const generatorActions = new ImageGeneratorActions(
    new GeneratorHandoffNavigator(window.location),
  );
  const list = new GenerationList(listRoot, statusFilter, {
    onSelect: (uid) => void controller?.select(uid),
    onFilter: () => void controller?.reload(),
  });
  const detail = new GenerationDetail(detailRoot, {
    onReconcile: (uid, promptId) => void controller?.reconcile(uid, promptId),
    createGeneratorActions: (uid) => generatorActions.create(uid),
  });
  controller = new GenerationsController({
    api,
    list,
    detail,
    requests: new RequestLifecycle(),
    status,
  });
  void controller.start();
  window.addEventListener(
    "pagehide",
    () => {
      controller?.dispose();
      generatorActions.dispose();
    },
    { once: true },
  );
}
