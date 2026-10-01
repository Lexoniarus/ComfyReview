import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageCurationController } from "../curation/image-curation-controller.js";
import { ImageGrid } from "../images/image-grid.js";
import { ImageViewer } from "../images/image-viewer.js";
import { PaginationControls } from "../images/pagination-controls.js";
import { ImageInspector } from "../inspector/image-inspector.js";
import { ResponsiveRails } from "../layout/responsive-rails.js";
import { ActiveScopeChips } from "../scopes/active-scope-chips.js";
import { ScopeNavigator } from "../scopes/scope-navigator.js";
import { ScopeStateController } from "../scopes/scope-state-controller.js";
import { TopWorstController } from "../surfaces/top-worst-controller.js";

const root = document.querySelector("[data-v2-surface='top-worst']");
if (root instanceof HTMLElement) {
  const state = new ScopeStateController(window);
  const gridRoot = root.querySelector("[data-image-grid]");
  const scopeRoot = root.querySelector("[data-scope-navigator]");
  const inspectorRoot = root.querySelector("[data-image-inspector]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  const activeScopesRoot = root.querySelector("[data-active-scopes]");
  const paginationRoot = root.querySelector("[data-pagination]");
  if (
    gridRoot instanceof HTMLElement &&
    scopeRoot instanceof HTMLElement &&
    inspectorRoot instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement &&
    activeScopesRoot instanceof HTMLElement &&
    paginationRoot instanceof HTMLElement
  ) {
    /** @type {TopWorstController | null} */
    let controller = null;
    /** @type {ImageCurationController | null} */
    let curation = null;
    const api = new ApiClient();
    const inspector = new ImageInspector(inspectorRoot, {
      onCuration: (imageUid, setKey) => void curation?.assign(imageUid, setKey),
    });
    const viewer = new ImageViewer(viewerRoot);
    const grid = new ImageGrid(gridRoot, {
      onSelect: (uid) => controller?.selectImage(uid),
      onExpand: (_uid, url) => viewer.open(url),
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
    const pagination = new PaginationControls(paginationRoot, {
      onPage: (offset) => {
        state.update({ offset });
        window.scrollTo({ top: 0, behavior: "smooth" });
      },
    });
    controller = new TopWorstController({
      api,
      state,
      navigator,
      activeScopes,
      grid,
      pagination,
      inspector,
      viewer,
      rails: new ResponsiveRails(root),
      facetRequests: new RequestLifecycle(),
      rankingRequests: new RequestLifecycle(),
      contextRequests: new RequestLifecycle(),
      root,
    });
    curation = new ImageCurationController({
      api,
      inspector,
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
      },
      { once: true },
    );
  }
}
