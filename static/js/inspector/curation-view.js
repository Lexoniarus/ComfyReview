/** Own the inspector's curation presentation state and control events. */
export class CurationView {
  /** @param {{onAssign?: (imageUid: string, setKey: string) => void}} [actions] */
  constructor(actions = {}) {
    this.onAssign = actions.onAssign || (() => {});
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-curation";
    this.events = new AbortController();
    /** @type {Record<string, any> | null} */
    this.currentImage = null;
    /** @type {string[]} */
    this.setKeys = [];
    this.isBusy = false;
    this.errorMessage = "";
    this.element.addEventListener("click", (event) => this.#assign(event), {
      signal: this.events.signal,
    });
    this.element.addEventListener("change", () => this.#syncButton(), {
      signal: this.events.signal,
    });
  }

  /** @param {Record<string, any>} image */
  render(image) {
    this.currentImage = image;
    const heading = document.createElement("h3");
    heading.textContent = "Curation";
    const controls = document.createElement("div");
    controls.className = "inspector-curation-controls";
    const select = document.createElement("select");
    select.dataset.curationSet = "";
    select.setAttribute("aria-label", "Curation-Set");
    select.append(option("", "Set auswählen"));
    for (const setKey of this.setKeys) {
      select.append(option(setKey, curationLabel(setKey)));
    }
    const current = image.curation || {};
    select.value = String(current.set_key || "");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button";
    button.dataset.curationAssign = "";
    button.textContent = "Zuweisen";
    const status = document.createElement("p");
    status.className = "inspector-curation-status is-error";
    status.dataset.curationStatus = "";
    status.textContent = this.errorMessage;
    status.hidden = !this.errorMessage;
    controls.append(select, button);
    this.element.replaceChildren(heading, controls, status);
    this.#syncButton();
  }

  /** @param {string[]} setKeys */
  setOptions(setKeys) {
    this.setKeys = [...setKeys];
    if (this.currentImage) this.render(this.currentImage);
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    this.isBusy = busy;
    this.#syncButton();
  }

  /** @param {string} message */
  showError(message) {
    this.errorMessage = message;
    const status = this.element.querySelector("[data-curation-status]");
    if (status instanceof HTMLElement) {
      status.textContent = message;
      status.hidden = !message;
    }
  }

  /** Release delegated curation listeners. */
  dispose() {
    this.events.abort();
  }

  /** @param {Event} event */
  #assign(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (!target.closest("[data-curation-assign]")) return;
    const select = this.element.querySelector("[data-curation-set]");
    const imageUid = String(this.currentImage?.image_uid || "");
    if (!(select instanceof HTMLSelectElement) || !imageUid || !select.value) {
      return;
    }
    this.onAssign(imageUid, select.value);
  }

  #syncButton() {
    const select = this.element.querySelector("[data-curation-set]");
    const button = this.element.querySelector("[data-curation-assign]");
    if (select instanceof HTMLSelectElement) select.disabled = this.isBusy;
    if (button instanceof HTMLButtonElement) {
      button.disabled =
        this.isBusy || !(select instanceof HTMLSelectElement && select.value);
    }
  }
}

/** @param {string} value @param {string} label */
function option(value, label) {
  const item = document.createElement("option");
  item.value = value;
  item.textContent = label;
  return item;
}

/** @param {string} setKey */
function curationLabel(setKey) {
  /** @type {Record<string, string>} */
  const labels = {
    character_face: "Charakter · Gesicht",
    character_body: "Charakter · Körper",
    scene: "Szene",
    outfit: "Outfit",
    pose: "Pose",
    expression: "Ausdruck",
  };
  return labels[setKey] || setKey.replaceAll("_", " ");
}
