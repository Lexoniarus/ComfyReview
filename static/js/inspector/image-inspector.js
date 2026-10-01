import { ContextView } from "./context-view.js";
import { CurationView } from "./curation-view.js";
import { GenerationView } from "./generation-view.js";
import { PromptView } from "./prompt-view.js";
import { ReviewsView } from "./reviews-view.js";
import { WorkflowView } from "./workflow-view.js";

/** Orchestrate focused views inside the shared image inspector. */
export class ImageInspector {
  /**
   * @param {HTMLElement} root
   * @param {{onCuration?: (imageUid: string, setKey: string) => void}} [actions]
   */
  constructor(root, actions = {}) {
    this.root = root;
    this.context = new ContextView();
    this.prompt = new PromptView();
    this.generation = new GenerationView();
    this.workflow = new WorkflowView();
    this.reviews = new ReviewsView();
    this.curation = new CurationView({ onAssign: actions.onCuration });
  }

  /** @param {Record<string, any>} image */
  render(image) {
    this.context.render(image);
    this.prompt.render(image);
    this.generation.render(image);
    this.workflow.render(image);
    this.curation.render(image);
    const heading = document.createElement("div");
    heading.className = "v2-panel-heading";
    heading.textContent = "Bilddetails";
    this.root.replaceChildren(
      heading,
      this.context.element,
      this.prompt.element,
      this.generation.element,
      this.workflow.element,
      this.reviews.element,
      this.curation.element,
    );
  }

  /** @param {Array<Record<string, any>>} events */
  renderReviews(events) {
    this.reviews.render(events);
  }

  /** Show the review-history loading state. */
  reviewsLoading() {
    this.reviews.loading();
  }

  /** @param {string} message */
  reviewsError(message) {
    this.reviews.error(message);
  }

  /** @param {string[]} setKeys */
  setCurationOptions(setKeys) {
    this.curation.setOptions(setKeys);
  }

  /** @param {boolean} busy */
  setCurationBusy(busy) {
    this.curation.setBusy(busy);
  }

  /** @param {string} message */
  showCurationError(message) {
    this.curation.showError(message);
  }

  /** Show the inspector's initial state. */
  empty() {
    this.#status("Wähle ein Bild aus, um Details zu sehen.");
  }

  /** Show a loading state for an incoming image context. */
  loading() {
    this.#status("Bilddetails werden geladen …");
  }

  /** @param {string} message */
  error(message) {
    this.#status(
      message || "Bilddetails konnten nicht geladen werden.",
      "is-error",
    );
  }

  /** Release owned child-view resources. */
  dispose() {
    this.curation.dispose();
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const status = document.createElement("p");
    status.className = `inspector-status ${className}`.trim();
    status.textContent = message;
    this.root.replaceChildren(status);
  }
}
