import { ApiClient } from "../core/api-client.js";
import { RequestLifecycle } from "../core/request-lifecycle.js";
import { SettingsView } from "../settings/settings-view.js";
import { SettingsController } from "../surfaces/settings-controller.js";

const root = document.querySelector("[data-v2-surface='settings']");
if (root instanceof HTMLElement) {
  const navigation = root.querySelector("[data-settings-navigation]");
  const content = root.querySelector("[data-settings-content]");
  const status = root.querySelector("[data-settings-status]");
  if (
    navigation instanceof HTMLElement &&
    content instanceof HTMLElement &&
    status instanceof HTMLElement
  ) {
    /** @type {SettingsController | null} */
    let controller = null;
    const view = new SettingsView(content, {
      onPreferencesSave: (/** @type {Record<string, any>} */ payload) =>
        void controller?.savePreferences(payload),
      onComfyUiCheck: () => void controller?.checkComfyUi(),
      onLoraClassify: (providerName, contentLevel) =>
        void controller?.classifyLora(providerName, contentLevel),
      onLoraPreview: (uid) => void controller?.previewLora(uid),
      onLoraApply: (uid, revision) =>
        void controller?.reclassifyLora(uid, revision),
    });
    controller = new SettingsController({
      api: new ApiClient(),
      requests: new RequestLifecycle(),
      view,
      navigation,
      status,
    });
    void controller.start();
    window.addEventListener("pagehide", () => controller?.dispose(), {
      once: true,
    });
  }
}
