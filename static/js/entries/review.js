import { ConfirmationDialog } from "../components/confirmation-dialog.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageCurationController } from "../curation/image-curation-controller.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { ImageInspector } from "../inspector/image-inspector.js";
import { ImageInspectorController } from "../inspector/image-inspector-controller.js";
import { ResponsiveRails } from "../layout/responsive-rails.js";
import { ReviewKeyboard } from "../review/review-keyboard.js";
import { ReviewStage } from "../review/review-stage.js";
import { ActiveScopeChips } from "../scopes/active-scope-chips.js";
import { ScopeNavigator } from "../scopes/scope-navigator.js";
import { ScopeStateController } from "../scopes/scope-state-controller.js";
import { ReviewController } from "../surfaces/review-controller.js";
import { GeneratorHandoffNavigator } from "../playground/playground-intent.js";

const root = document.querySelector("[data-v2-surface='review']");
if (root instanceof HTMLElement) {
  const scopeRoot = root.querySelector("[data-scope-navigator]");
  const activeScopesRoot = root.querySelector("[data-active-scopes]");
  const stageRoot = root.querySelector("[data-review-stage]");
  const inspectorRoot = root.querySelector("[data-image-inspector]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  const dialogRoot = root.querySelector("[data-confirm-dialog]");
  const status = root.querySelector("[data-review-status]");
  if (
    scopeRoot instanceof HTMLElement &&
    activeScopesRoot instanceof HTMLElement &&
    stageRoot instanceof HTMLElement &&
    inspectorRoot instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement &&
    dialogRoot instanceof HTMLDialogElement &&
    status instanceof HTMLElement
  ) {
    const state = new ScopeStateController(window);
    const viewer = new ImageViewer(viewerRoot);
    const dialog = new ConfirmationDialog(dialogRoot);
    /** @type {ReviewController | null} */
    let controller = null;
    /** @type {ImageCurationController | null} */
    let curation = null;
    const api = new ApiClient();
    const generatorActions = new ImageGeneratorActions(
      new GeneratorHandoffNavigator(window.location),
    );
    const inspectorView = new ImageInspector(inspectorRoot, {
      onCuration: (imageUid, setKey) => void curation?.assign(imageUid, setKey),
      createGeneratorActions: (uid) =>
        generatorActions.create(uid, "prominent"),
    });
    const inspector = new ImageInspectorController({
      api,
      view: inspectorView,
      requests: new RequestLifecycle(),
    });
    const navigator = new ScopeNavigator(scopeRoot, {
      onToggle: (uid) => {
        const scopes = state.state.scopes.includes(uid)
          ? state.state.scopes.filter((candidate) => candidate !== uid)
          : [...state.state.scopes, uid];
        state.update({ scopes });
      },
      onClassification: (classification) =>
        state.update({
          classification:
            classification === "classified" || classification === "unclassified"
              ? classification
              : "all",
        }),
    });
    const activeScopes = new ActiveScopeChips(activeScopesRoot, {
      onRemove: (uid) =>
        state.update({
          scopes: state.state.scopes.filter((candidate) => candidate !== uid),
        }),
      onClear: () => state.update({ scopes: [] }),
    });
    const stage = new ReviewStage(stageRoot, {
      onRate: (rating) => void controller?.submitRating(rating),
      onDelete: () => void controller?.deleteCurrent(),
      onExpand: (url) => controller?.expand(url),
      createGeneratorActions: (uid) => generatorActions.create(uid),
    });
    const keyboard = new ReviewKeyboard(document, {
      onRate: (rating) => void controller?.submitRating(rating),
      onDelete: () => void controller?.deleteCurrent(),
      isDialogOpen: () => dialog.isOpen(),
    });
    controller = new ReviewController({
      api,
      state,
      navigator,
      activeScopes,
      stage,
      inspector,
      viewer,
      rails: new ResponsiveRails(root),
      dialog,
      keyboard,
      readRequests: new RequestLifecycle(),
      mutationRequests: new RequestLifecycle(),
      status,
    });
    curation = new ImageCurationController({
      api,
      inspector: inspectorView,
      requests: new RequestLifecycle(),
      onAssigned: (imageUid) =>
        controller?.refresh(imageUid) || Promise.resolve(),
    });
    controller.start();
    void curation.start();
    window.addEventListener(
      "pagehide",
      () => {
        curation?.dispose();
        controller?.dispose();
        generatorActions.dispose();
      },
      { once: true },
    );
  }
}
