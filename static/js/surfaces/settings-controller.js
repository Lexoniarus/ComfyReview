/** Orchestrate settings requests, navigation and focused editors. */
export class SettingsController {
  /** @param {{api: any, requests: any, view: any, navigation: HTMLElement, status: HTMLElement}} options */
  constructor(options) {
    this.api = options.api;
    this.requests = options.requests;
    this.view = options.view;
    this.navigation = options.navigation;
    this.status = options.status;
    /** @type {Record<string, any> | null} */
    this.data = null;
    this.section = "general";
    this.abortController = new AbortController();
  }

  /** Load canonical settings and activate navigation. */
  async start() {
    this.navigation.addEventListener(
      "click",
      (/** @type {Event} */ event) => {
        const button =
          event.target instanceof Element
            ? event.target.closest("[data-section]")
            : null;
        if (button instanceof HTMLButtonElement)
          this.show(button.dataset.section || "general");
      },
      { signal: this.abortController.signal },
    );
    await this.reload();
  }

  /** @param {string} section */
  show(section) {
    this.section = section;
    for (const button of this.navigation.querySelectorAll("[data-section]")) {
      button.setAttribute(
        "aria-current",
        String(button.getAttribute("data-section") === section),
      );
    }
    if (this.data) this.view.render(section, this.data);
  }

  /** Refresh all settings after one mutation. */
  async reload() {
    this.#status("Einstellungen werden geladen …");
    try {
      this.data = await this.requests.run((/** @type {AbortSignal} */ signal) =>
        this.api.get("settings", { signal }),
      );
      this.#status("");
      this.show(this.section);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        this.#status(
          errorMessage(error, "Einstellungen konnten nicht geladen werden."),
        );
      }
    }
  }

  /** @param {Record<string, any>} payload */
  async savePreferences(payload) {
    await this.#mutate(() => this.api.put("settings/preferences", payload));
  }

  /** @param {string | null} uid @param {Record<string, any>} payload */
  async saveProfile(uid, payload) {
    await this.#mutate(() =>
      uid
        ? this.api.put(
            `settings/generation-profiles/${encodeURIComponent(uid)}`,
            payload,
          )
        : this.api.post("settings/generation-profiles", payload),
    );
  }

  /** @param {string} uid @param {boolean} archived */
  async archiveProfile(uid, archived) {
    await this.#mutate(() =>
      this.api.patch(
        `settings/generation-profiles/${encodeURIComponent(uid)}/archive`,
        { archived },
      ),
    );
  }

  /** @param {string} uid */
  async defaultProfile(uid) {
    await this.#mutate(() =>
      this.api.put(
        `settings/generation-profiles/${encodeURIComponent(uid)}/default`,
        {},
      ),
    );
  }

  /** Run a read-only provider check and refresh the ComfyUI section. */
  async checkComfyUi() {
    await this.#mutate(() => this.api.post("settings/comfyui/check", {}));
  }

  /** Release requests, listeners and child views. */
  dispose() {
    this.abortController.abort();
    this.requests.dispose();
    this.view.dispose();
    this.data = null;
  }

  /** @param {() => Promise<unknown>} operation */
  async #mutate(operation) {
    this.#status("Wird gespeichert …");
    try {
      await operation();
      await this.reload();
      this.#status("Gespeichert.");
    } catch (error) {
      this.#status(errorMessage(error, "Speichern fehlgeschlagen."));
    }
  }

  /** @param {string} message */
  #status(message) {
    this.status.textContent = message;
  }
}

/** @param {unknown} error @param {string} fallback */
function errorMessage(error, fallback) {
  return error instanceof Error ? error.message : fallback;
}
