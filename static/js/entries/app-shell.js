import { PlaygroundIntentTray } from "../analytics/playground-intent-tray.js";
import { PlaygroundIntentStore } from "../playground/playground-intent.js";

const root = document.querySelector("[data-global-intent-tray]");
const toast = document.querySelector("[data-global-intent-toast]");
if (root instanceof HTMLElement && toast instanceof HTMLElement) {
  const store = new PlaygroundIntentStore(window.sessionStorage);
  const tray = new PlaygroundIntentTray(root, toast, store, window.location);
  /** @param {Event} event */
  const onStaged = (event) => {
    const detail = event instanceof CustomEvent ? event.detail : null;
    tray.render();
    tray.notify(String(detail?.message || "Für den Generator vorgemerkt"));
  };
  window.addEventListener("comfyreview:intent-staged", onStaged);
  window.addEventListener(
    "pagehide",
    () => {
      window.removeEventListener("comfyreview:intent-staged", onStaged);
      tray.dispose();
    },
    { once: true },
  );
}
