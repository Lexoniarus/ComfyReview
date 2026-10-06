/** Own manual content-level and image-lifecycle controls in the inspector. */
export class ContentLevelView {
  /** @param {{onAssign?: (imageUid: string, level: string | null) => void, onDelete?: (imageUid: string) => void}} actions */
  constructor(actions = {}) {
    this.actions = actions;
    this.imageUid = "";
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-content-level";
    this.abortController = new AbortController();
  }

  /** @param {Record<string, any>} image */
  render(image) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.imageUid = String(image.image_uid || "");
    const classification = image.content_classification || {};
    const heading = document.createElement("h3");
    heading.textContent = "Inhaltsstufe";
    const detail = document.createElement("p");
    detail.textContent = `Automatisch: ${label(classification.inferred_level || "standard")}`;
    const select = document.createElement("select");
    select.dataset.contentLevel = "";
    for (const [value, text] of [
      ["", "Automatische Einstufung verwenden"],
      ["standard", "Standard"],
      ["sexy", "Sexy"],
      ["lewd", "Lewd"],
      ["nude", "Nude"],
      ["explicit", "Explicit"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      select.append(option);
    }
    select.value = classification.override_level || "";
    const assign = actionButton("Einstufung speichern", "assign");
    const remove = actionButton("Bild löschen", "delete");
    remove.className = "review-delete-button";
    const status = document.createElement("p");
    status.dataset.contentLevelStatus = "";
    /** @type {Element[]} */
    const children = [heading, detail];
    if (this.actions.onAssign) children.push(select, assign);
    if (this.actions.onDelete) children.push(remove);
    children.push(status);
    this.element.replaceChildren(...children);
    this.element.addEventListener(
      "click",
      (event) => this.#handleClick(event),
      {
        signal: this.abortController.signal,
      },
    );
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const control of this.element.querySelectorAll("button, select")) {
      if (
        control instanceof HTMLButtonElement ||
        control instanceof HTMLSelectElement
      ) {
        control.disabled = busy;
      }
    }
  }

  /** @param {string} message */
  showError(message) {
    const status = this.element.querySelector("[data-content-level-status]");
    if (status) status.textContent = message;
  }

  dispose() {
    this.abortController.abort();
  }

  /** @param {Event} event */
  #handleClick(event) {
    const target = event.target;
    if (!(target instanceof Element) || !this.imageUid) return;
    const action = target.closest("[data-content-action]");
    if (!(action instanceof HTMLElement)) return;
    if (action.dataset.contentAction === "delete") {
      this.actions.onDelete?.(this.imageUid);
      return;
    }
    const select = this.element.querySelector("[data-content-level]");
    if (select instanceof HTMLSelectElement) {
      this.actions.onAssign?.(this.imageUid, select.value || null);
    }
  }
}

/** @param {string} text @param {string} action */
function actionButton(text, action) {
  const control = document.createElement("button");
  control.type = "button";
  control.textContent = text;
  control.dataset.contentAction = action;
  return control;
}

/** @param {string} value */
function label(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
