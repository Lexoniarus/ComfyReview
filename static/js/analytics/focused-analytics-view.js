import { CompositionEvidenceView } from "./composition-evidence-view.js";
import { EvidenceImageStrip } from "./evidence-image-strip.js";
import { OverviewAnalyticsView } from "./overview-analytics-view.js";
import { ParameterEvidenceView } from "./parameter-evidence-view.js";
import { RenderSetupView } from "./render-setup-view.js";
import { ScopeEvidenceView } from "./scope-evidence-view.js";

/** Compose focused analytics views without owning requests or query state. */
export class AnalyticsView {
  /** @param {HTMLElement} root @param {{onImageSelect?: (imageUid: string, imageUrl: string) => void, createGeneratorActions?: (imageUid: string) => HTMLElement}} [actions] */
  constructor(root, actions = {}) {
    this.root = root;
    this.images = new EvidenceImageStrip({
      onSelect: actions.onImageSelect,
      createGeneratorActions: actions.createGeneratorActions,
    });
    this.setups = new RenderSetupView({ images: this.images });
    this.overview = new OverviewAnalyticsView();
    this.scopes = new ScopeEvidenceView({ images: this.images });
    this.parameters = new ParameterEvidenceView({ images: this.images });
    this.compositions = new CompositionEvidenceView({
      images: this.images,
      setups: this.setups,
    });
    this.section = "overview";
    this.viewName = "";
    this.basis = "observed";
    this.scope = "setup";
  }

  /** @param {string} section @param {Record<string, any>} payload */
  render(section, payload) {
    this.clear();
    this.section = section;
    this.viewName = String(payload.view || "");
    this.basis = String(payload.basis || "observed");
    this.scope = String(payload.scope || "setup");
    if (section === "overview") this.overview.render(this.root, payload);
    else if (section === "scopes") this.scopes.render(this.root, payload);
    else if (section === "parameters")
      this.parameters.render(this.root, payload);
    else this.compositions.render(this.root, payload);
    return this.#sentinel();
  }

  /** @param {Record<string, any>} payload */
  append(payload) {
    if (this.section === "scopes") this.scopes.append(payload.items);
    else if (this.section === "parameters") {
      this.parameters.append(payload.items, this.scope, this.basis);
    } else if (this.section === "combinations") {
      this.compositions.append(payload.items);
    }
  }

  /** @param {string} compositionUid @param {Record<string, any>} payload */
  renderCompositionSetups(compositionUid, payload) {
    this.compositions.renderSetups(compositionUid, payload);
  }

  /** Clear rendered report content. */
  clear() {
    this.root.replaceChildren();
  }

  /** Release listeners owned by child views. */
  dispose() {
    this.images.dispose();
    this.overview.dispose();
    this.scopes.dispose();
    this.parameters.dispose();
    this.clear();
  }

  #sentinel() {
    const sentinel = document.createElement("div");
    sentinel.className = "analytics-sentinel";
    sentinel.dataset.analyticsSentinel = "";
    sentinel.setAttribute("aria-hidden", "true");
    this.root.append(sentinel);
    return sentinel;
  }
}
