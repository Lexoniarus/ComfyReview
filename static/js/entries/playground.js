import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { GeneratorHandoffApplier } from "../playground/generator-handoff-applier.js";
import { GenerationControls } from "../playground/generation-controls.js";
import {
  GeneratorHandoffNavigator,
  GeneratorHandoffUrlCleaner,
  readPlaygroundIntent,
} from "../playground/playground-intent.js";
import { GeneratorStatePersistence } from "../playground/generator-state-persistence.js";
import { PromptModeEditor } from "../playground/prompt-mode-editor.js";
import { PlaygroundWorkspace } from "../playground/playground-workspace.js";
import { RenderGuidancePanel } from "../playground/render-guidance-panel.js";
import { VariantBoard } from "../playground/variant-board.js";
import { VariantInspector } from "../playground/variant-inspector.js";
import { VariantSession } from "../playground/variant-session.js";
import { PlaygroundController } from "../surfaces/playground-controller.js";

const root = document.querySelector("[data-v2-surface='playground']");
if (root instanceof HTMLElement) {
  const modesRoot = root.querySelector("[data-prompt-modes]");
  const inspectorRoot = root.querySelector("[data-variant-inspector]");
  const inspectorState = root.querySelector("[data-variant-state]");
  const boardRoot = root.querySelector("[data-variant-board]");
  const workspaceRoot = root.querySelector("[data-playground-workspace]");
  const controlsRoot = root.querySelector("[data-generation-controls]");
  const guidanceRoot = root.querySelector("[data-render-guidance]");
  const prepareButton = root.querySelector("[data-prepare-variants]");
  const refreshButton = root.querySelector("[data-refresh-variants]");
  const submitButton = root.querySelector("[data-submit-generation]");
  const status = root.querySelector("[data-playground-status]");
  const result = root.querySelector("[data-generation-result]");
  const variantSummary = root.querySelector("[data-variant-summary]");
  const selectedCount = root.querySelector("[data-selected-count]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  if (
    modesRoot instanceof HTMLElement &&
    inspectorRoot instanceof HTMLElement &&
    inspectorState instanceof HTMLElement &&
    boardRoot instanceof HTMLElement &&
    workspaceRoot instanceof HTMLElement &&
    controlsRoot instanceof HTMLElement &&
    guidanceRoot instanceof HTMLElement &&
    prepareButton instanceof HTMLButtonElement &&
    refreshButton instanceof HTMLButtonElement &&
    submitButton instanceof HTMLButtonElement &&
    status instanceof HTMLElement &&
    result instanceof HTMLElement &&
    variantSummary instanceof HTMLElement &&
    selectedCount instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement
  ) {
    /** @type {PlaygroundController | null} */
    let controller = null;
    const api = new ApiClient();
    const viewer = new ImageViewer(viewerRoot);
    const generatorActions = new ImageGeneratorActions(
      new GeneratorHandoffNavigator(window.location),
    );
    const inspector = new VariantInspector(
      inspectorRoot,
      inspectorState,
      () => controller?.variantEdited(),
      (url) => viewer.open(url),
      (imageUid) => generatorActions.create(imageUid),
    );
    const board = new VariantBoard(boardRoot, {
      onSelect: (draftUid, selected) =>
        controller?.selectVariant(draftUid, selected),
      onInspect: (draftUid) => controller?.inspectVariant(draftUid),
    });
    const workspace = new PlaygroundWorkspace(workspaceRoot);
    const session = new VariantSession(new RequestLifecycle());
    const modes = new PromptModeEditor(
      modesRoot,
      () => controller?.promptSettingsChanged(),
      {
        loadComponent: (uid, signal) =>
          api.get(`catalog/components/${encodeURIComponent(uid)}`, { signal }),
        loadGuidance: (payload, signal) =>
          api.post("playground/prompt-guidance", payload, { signal }),
        materializeCandidate: (payload, signal) =>
          api.post("playground/prompt-candidates", payload, { signal }),
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
    const persistence = new GeneratorStatePersistence({
      api,
      snapshot: () => ({
        ...modes.stateValue(),
        ...controls.stateValue(),
      }),
      onError: (error) => {
        status.textContent = `Einstellungen konnten nicht gespeichert werden: ${errorMessage(error)}`;
      },
    });
    const handoffRequests = new RequestLifecycle();
    const handoffApplier = new GeneratorHandoffApplier({
      api,
      modes,
      controls,
      persistence,
      requests: handoffRequests,
      urlCleaner: new GeneratorHandoffUrlCleaner(
        window.location,
        window.history,
      ),
    });
    controller = new PlaygroundController({
      api,
      modes,
      controls,
      inspector,
      board,
      workspace,
      session,
      guidance,
      requests: new RequestLifecycle(),
      previewRequests: new RequestLifecycle(),
      guidanceRequests: new RequestLifecycle(),
      persistence,
      handoffApplier,
      prepareButton,
      refreshButton,
      submitButton,
      status,
      result,
      variantSummary,
      selectedCount,
      intent: presentIntent(readPlaygroundIntent(window.location.search)),
    });
    void controller.start();
    window.addEventListener(
      "pagehide",
      () => {
        void persistence.flush().catch((error) => {
          status.textContent = `Einstellungen konnten nicht gespeichert werden: ${errorMessage(error)}`;
        });
        handoffRequests.dispose();
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

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
