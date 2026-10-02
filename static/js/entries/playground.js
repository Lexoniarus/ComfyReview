import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { DraftPreview } from "../playground/draft-preview.js";
import { GenerationControls } from "../playground/generation-controls.js";
import { PromptModeEditor } from "../playground/prompt-mode-editor.js";
import { TopCombinationsView } from "../playground/top-combinations.js";
import { PlaygroundController } from "../surfaces/playground-controller.js";

const root = document.querySelector("[data-v2-surface='playground']");
if (root instanceof HTMLElement) {
  const modesRoot = root.querySelector("[data-prompt-modes]");
  const seedInput = root.querySelector("[data-selection-seed]");
  const draftRoot = root.querySelector("[data-draft-preview]");
  const draftState = root.querySelector("[data-draft-state]");
  const controlsRoot = root.querySelector("[data-generation-controls]");
  const prepareButton = root.querySelector("[data-prepare-draft]");
  const submitButton = root.querySelector("[data-submit-generation]");
  const status = root.querySelector("[data-playground-status]");
  const result = root.querySelector("[data-generation-result]");
  const combinationsRoot = root.querySelector("[data-top-combinations]");
  if (
    modesRoot instanceof HTMLElement &&
    seedInput instanceof HTMLInputElement &&
    draftRoot instanceof HTMLElement &&
    draftState instanceof HTMLElement &&
    controlsRoot instanceof HTMLElement &&
    prepareButton instanceof HTMLButtonElement &&
    submitButton instanceof HTMLButtonElement &&
    status instanceof HTMLElement &&
    result instanceof HTMLElement &&
    combinationsRoot instanceof HTMLElement
  ) {
    const controller = new PlaygroundController({
      api: new ApiClient(),
      modes: new PromptModeEditor(modesRoot, seedInput),
      controls: new GenerationControls(controlsRoot),
      draft: new DraftPreview(draftRoot, draftState),
      combinations: new TopCombinationsView(combinationsRoot),
      requests: new RequestLifecycle(),
      prepareButton,
      submitButton,
      status,
      result,
      newDraftUid: () => crypto.randomUUID(),
    });
    void controller.start();
    window.addEventListener("pagehide", () => controller.dispose(), {
      once: true,
    });
  }
}
