import { CatalogBrowser } from "../catalog/catalog-browser.js";
import { CatalogEditor } from "../catalog/catalog-editor.js";
import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { ImageViewer } from "../images/image-viewer.js";
import { ImageGeneratorActions } from "../images/image-generator-actions.js";
import { PlaygroundIntentStore } from "../playground/playground-intent.js";
import { CatalogController } from "../surfaces/catalog-controller.js";

const root = document.querySelector("[data-v2-surface='catalog']");
if (root instanceof HTMLElement) {
  const kindsRoot = root.querySelector("[data-catalog-kinds]");
  const listRoot = root.querySelector("[data-catalog-list]");
  const search = root.querySelector("[data-catalog-search]");
  const editorRoot = root.querySelector("[data-catalog-editor]");
  const newButton = root.querySelector("[data-catalog-new]");
  const status = root.querySelector("[data-catalog-status]");
  const viewerRoot = root.querySelector("[data-image-viewer]");
  if (
    kindsRoot instanceof HTMLElement &&
    listRoot instanceof HTMLElement &&
    search instanceof HTMLInputElement &&
    editorRoot instanceof HTMLElement &&
    newButton instanceof HTMLButtonElement &&
    status instanceof HTMLElement &&
    viewerRoot instanceof HTMLDialogElement
  ) {
    /** @type {CatalogController | null} */
    let controller = null;
    const api = new ApiClient();
    const viewer = new ImageViewer(viewerRoot);
    const generatorActions = new ImageGeneratorActions({
      api,
      store: new PlaygroundIntentStore(window.sessionStorage),
    });
    const browser = new CatalogBrowser(kindsRoot, listRoot, search, {
      onSelect: (uid, catalogKind) => void controller?.select(uid, catalogKind),
    });
    const editor = new CatalogEditor(editorRoot, {
      onSave: (payload) => void controller?.save(payload),
      onArchive: (archived) => void controller?.setArchived(archived),
      onEvidenceOpen: (_imageUid, imageUrl) => viewer.open(imageUrl),
      createGeneratorActions: (imageUid) => generatorActions.create(imageUid),
    });
    controller = new CatalogController({
      api,
      browser,
      editor,
      requests: new RequestLifecycle(),
      newButton,
      status,
    });
    void controller.start();
    window.addEventListener(
      "pagehide",
      () => {
        controller?.dispose();
        viewer.close();
        generatorActions.dispose();
      },
      { once: true },
    );
  }
}
