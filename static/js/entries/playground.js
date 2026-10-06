import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { DraftPreview } from "../playground/draft-preview.js";
import { GenerationControls } from "../playground/generation-controls.js";
import {
  PlaygroundIntentStore,
  readPlaygroundIntent,
} from "../playground/playground-intent.js";
import { PromptModeEditor } from "../playground/prompt-mode-editor.js";
import { RenderGuidancePanel } from "../playground/render-guidance-panel.js";
import { PlaygroundController } from "../surfaces/playground-controller.js";

const root = document.querySelector("[data-v2-surface='playground']");
if (root instanceof HTMLElement) {
  const modesRoot = root.querySelector("[data-prompt-modes]");
  const draftRoot = root.querySelector("[data-draft-preview]");
  const draftState = root.querySelector("[data-draft-state]");
  const controlsRoot = root.querySelector("[data-generation-controls]");
  const guidanceRoot = root.querySelector("[data-render-guidance]");
  const prepareButton = root.querySelector("[data-prepare-draft]");
  const submitButton = root.querySelector("[data-submit-generation]");
  const status = root.querySelector("[data-playground-status]");
  const result = root.querySelector("[data-generation-result]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  if (
    modesRoot instanceof HTMLElement &&
    draftRoot instanceof HTMLElement &&
    draftState instanceof HTMLElement &&
    controlsRoot instanceof HTMLElement &&
    guidanceRoot instanceof HTMLElement &&
    prepareButton instanceof HTMLButtonElement &&
    submitButton instanceof HTMLButtonElement &&
    status instanceof HTMLElement &&
    result instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement
  ) {
    /** @type {PlaygroundController | null} */
    let controller = null;
    const api = new ApiClient();
    const intentStore = new PlaygroundIntentStore(window.sessionStorage);
    const viewer = new ImageViewer(viewerRoot);
    const generatorActions = new ImageGeneratorActions({
      api,
      store: intentStore,
    });
    const draft = new DraftPreview(
      draftRoot,
      draftState,
      () => void controller?.refreshPreview(),
      (url) => viewer.open(url),
      (imageUid) => generatorActions.create(imageUid),
    );
    const modes = new PromptModeEditor(
      modesRoot,
      () => controller?.clearDraftReference(),
      {
        loadComponent: (uid, signal) =>
          api.get(`catalog/components/${encodeURIComponent(uid)}`, { signal }),
        onImageSelect: (url) => viewer.open(url),
      },
    );
    const controls = new GenerationControls(controlsRoot, () =>
      controller?.settingsChanged(),
    );
    const guidance = new RenderGuidancePanel(guidanceRoot, {
      onApplySetup: (settings) => controller?.applyGuidanceSetup(settings),
      onApplyParameter: (parameter, value) =>
        controller?.applyGuidanceParameter(parameter, value),
      onModeChange: (basis) => controller?.guidanceModeChanged(basis),
    });
    controller = new PlaygroundController({
      api,
      modes,
      controls,
      draft,
      guidance,
      requests: new RequestLifecycle(),
      previewRequests: new RequestLifecycle(),
      guidanceRequests: new RequestLifecycle(),
      prepareButton,
      submitButton,
      status,
      result,
      intent: {
        ...intentStore.read(),
        ...presentIntent(readPlaygroundIntent(window.location.search)),
      },
      intentStore,
    });
    void controller.start();
    window.addEventListener(
      "pagehide",
      () => {
        controller.dispose();
        viewer.dispose();
        generatorActions.dispose();
      },
      {
        once: true,
      },
    );
  }
}

/** Remove empty URL defaults so staged values survive generator navigation. */
/** @param {Record<string, any>} intent */
function presentIntent(intent) {
  return Object.fromEntries(
    Object.entries(intent).filter(([, value]) =>
      Array.isArray(value)
        ? value.length > 0
        : value !== "" && value !== null && value !== undefined,
    ),
  );
}
