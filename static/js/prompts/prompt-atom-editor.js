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
    const text = document.createElement("input");
    text.type = "text";
    text.dataset.atomText = "";
    text.value = String(usage.text || "");
    text.addEventListener("input", () => this.onChange(), {
      signal: this.abortController.signal,
    });
    const weight = document.createElement("input");
    weight.type = "number";
    weight.step = "0.001";
    weight.min = "0.001";
    weight.dataset.atomWeight = "";
    weight.value = String(usage.weight ?? 1);
    weight.addEventListener("input", () => this.onChange(), {
      signal: this.abortController.signal,
    });
    row.append(text, weight);
    for (const [label, action] of [
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
    if (action === "remove") row.remove();
    else if (action === "up" && row.previousElementSibling)
      this.list.insertBefore(row, row.previousElementSibling);
    else if (action === "down" && row.nextElementSibling)
      this.list.insertBefore(row.nextElementSibling, row);
    this.onChange();
  }
}

/** @param {Element} row */
function rowValue(row) {
  const text = row.querySelector("[data-atom-text]");
  const weight = row.querySelector("[data-atom-weight]");
  return {
    text: text instanceof HTMLInputElement ? text.value.trim() : "",
    weight: weight instanceof HTMLInputElement ? Number(weight.value) : 1,
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
