/** Own one ordered positive or negative prompt-atom draft. */
export class PromptAtomEditor {
  /** @param {string} label @param {Array<Record<string, any>>} usages @param {() => void} [onChange] */
  constructor(label, usages, onChange = () => {}) {
    this.label = label;
    this.original = normalizedUsages(usages);
    this.onChange = onChange;
    this.abortController = new AbortController();
    this.element = document.createElement("section");
    this.element.className = "prompt-atom-editor";
    this.list = document.createElement("div");
    this.list.className = "prompt-atom-list";
    this.pointerDrag = null;
    const heading = document.createElement("h3");
    heading.textContent = label;
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "Atom hinzufügen";
    add.addEventListener(
      "click",
      () => {
        this.#append({});
        this.onChange();
      },
      {
        signal: this.abortController.signal,
      },
    );
    const reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "Revision zurücksetzen";
    reset.addEventListener("click", () => this.reset(), {
      signal: this.abortController.signal,
    });
    this.element.append(heading, this.list, add, reset);
    this.list.addEventListener("dragover", (event) => this.#dragOver(event), {
      signal: this.abortController.signal,
    });
    this.list.addEventListener(
      "pointerdown",
      (event) => this.#pointerDown(event),
      { signal: this.abortController.signal },
    );
    this.list.addEventListener(
      "pointermove",
      (event) => this.#pointerMove(event),
      { signal: this.abortController.signal },
    );
    this.list.addEventListener("pointerup", (event) => this.#pointerUp(event), {
      signal: this.abortController.signal,
    });
    this.list.addEventListener(
      "pointercancel",
      (event) => this.#pointerUp(event),
      { signal: this.abortController.signal },
    );
    this.#renderOriginal();
  }

  /** Return the current ordered structured atom values. */
  value() {
    return [...this.list.querySelectorAll(".prompt-atom-row")]
      .map((row) => rowValue(row))
      .filter((usage) => usage.text);
  }

  /** Restore the exact selected catalog revision. */
  reset() {
    this.#renderOriginal();
    this.onChange();
  }

  #renderOriginal() {
    this.list.replaceChildren();
    for (const usage of this.original) this.#append(usage);
  }

  /** Release all owned listeners. */
  dispose() {
    this.abortController.abort();
  }

  /** @param {Record<string, any>} usage */
  #append(usage) {
    const row = document.createElement("div");
    row.className = "prompt-atom-row";
    row.draggable = true;
    row.addEventListener("dragstart", () => row.classList.add("is-dragging"), {
      signal: this.abortController.signal,
    });
    row.addEventListener(
      "dragend",
      () => {
        row.classList.remove("is-dragging");
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    const text = document.createElement("input");
    text.type = "text";
    text.dataset.atomText = "";
    text.value = String(usage.text || "");
    text.addEventListener("input", () => this.onChange(), {
      signal: this.abortController.signal,
    });
    const weight = document.createElement("input");
    weight.type = "number";
    weight.step = "0.01";
    weight.min = "0.01";
    weight.dataset.atomWeight = "";
    weight.value = String(usage.weight ?? 1);
    weight.addEventListener("input", () => this.onChange(), {
      signal: this.abortController.signal,
    });
    row.append(text, weight);
    const handle = document.createElement("button");
    handle.type = "button";
    handle.className = "prompt-atom-drag-handle";
    handle.dataset.dragHandle = "";
    handle.setAttribute("aria-label", "Atom verschieben");
    handle.textContent = "↕";
    row.append(handle);
    for (const [label, action] of [
      ["−0,01", "decrease"],
      ["+0,01", "increase"],
      ["Nach oben", "up"],
      ["Nach unten", "down"],
      ["Entfernen", "remove"],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => this.#move(row, action), {
        signal: this.abortController.signal,
      });
      row.append(button);
    }
    this.list.append(row);
  }

  /** @param {HTMLElement} row @param {string} action */
  #move(row, action) {
    if (action === "decrease" || action === "increase") {
      const input = row.querySelector("[data-atom-weight]");
      if (input instanceof HTMLInputElement) {
        const delta = action === "increase" ? 0.01 : -0.01;
        input.value = Math.max(0.01, Number(input.value || 1) + delta).toFixed(
          2,
        );
      }
    } else if (action === "remove") row.remove();
    else if (action === "up" && row.previousElementSibling)
      this.list.insertBefore(row, row.previousElementSibling);
    else if (action === "down" && row.nextElementSibling)
      this.list.insertBefore(row.nextElementSibling, row);
    this.onChange();
  }

  /** @param {DragEvent} event */
  #dragOver(event) {
    event.preventDefault();
    const dragging = this.list.querySelector(".is-dragging");
    if (!(dragging instanceof HTMLElement)) return;
    this.#moveDragging(dragging, event.clientY);
  }

  /** @param {PointerEvent} event */
  #pointerDown(event) {
    if (!(event.target instanceof Element)) return;
    const handle = event.target.closest("[data-drag-handle]");
    const row = handle?.closest(".prompt-atom-row");
    if (!(handle instanceof HTMLElement) || !(row instanceof HTMLElement))
      return;
    event.preventDefault();
    this.pointerDrag = { row, pointerId: event.pointerId };
    row.classList.add("is-dragging");
    handle.setPointerCapture?.(event.pointerId);
  }

  /** @param {PointerEvent} event */
  #pointerMove(event) {
    if (!this.pointerDrag || this.pointerDrag.pointerId !== event.pointerId)
      return;
    event.preventDefault();
    this.#moveDragging(this.pointerDrag.row, event.clientY);
  }

  /** @param {PointerEvent} event */
  #pointerUp(event) {
    if (!this.pointerDrag || this.pointerDrag.pointerId !== event.pointerId)
      return;
    this.pointerDrag.row.classList.remove("is-dragging");
    this.pointerDrag = null;
    this.onChange();
  }

  /** @param {HTMLElement} dragging @param {number} clientY */
  #moveDragging(dragging, clientY) {
    const candidates = [
      ...this.list.querySelectorAll(".prompt-atom-row:not(.is-dragging)"),
    ];
    const next = candidates.find((candidate) => {
      const bounds = candidate.getBoundingClientRect();
      return clientY < bounds.top + bounds.height / 2;
    });
    this.list.insertBefore(dragging, next || null);
  }
}

/** @param {Element} row */
function rowValue(row) {
  const text = row.querySelector("[data-atom-text]");
  const weight = row.querySelector("[data-atom-weight]");
  return {
    text: text instanceof HTMLInputElement ? text.value.trim() : "",
    weight:
      weight instanceof HTMLInputElement
        ? Math.max(0.01, Number(weight.value))
        : 1,
  };
}

/** @param {unknown} values */
function normalizedUsages(values) {
  if (!Array.isArray(values)) return [];
  return values.map((usage) => ({
    text: String(usage.text || ""),
    weight: Number(usage.weight ?? 1),
  }));
}
