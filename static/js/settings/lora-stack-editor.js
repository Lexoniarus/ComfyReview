/** Own an ordered editable LoRA stack and its DOM lifecycle. */
export class LoraStackEditor {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    /** @type {string[]} */
    this.available = [];
    /** @type {Array<Record<string, any>>} */
    this.items = [];
    this.abortController = new AbortController();
  }

  /** @param {Array<Record<string, any>>} items @param {string[]} available */
  render(items, available) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.available = [...available];
    this.items = items.map((item) => ({
      name: String(item.name || ""),
      model_strength: Number(item.model_strength ?? 1),
      clip_strength: Number(item.clip_strength ?? 1),
    }));
    this.#draw();
  }

  /** Return the ordered browser draft. */
  value() {
    return this.items.map((item) => ({ ...item }));
  }

  /** Release listeners and retained state. */
  dispose() {
    this.abortController.abort();
    this.items = [];
    this.root.replaceChildren();
  }

  #draw() {
    this.root.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = "LoRA-Stack";
    const list = document.createElement("div");
    list.className = "settings-lora-list";
    this.items.forEach((item, index) => list.append(this.#row(item, index)));
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "LoRA hinzufügen";
    add.addEventListener(
      "click",
      () => {
        const selected = this.available.find(
          (name) => !this.items.some((item) => item.name === name),
        );
        if (!selected) return;
        this.items.push({
          name: selected,
          model_strength: 1,
          clip_strength: 1,
        });
        this.#draw();
      },
      { signal: this.abortController.signal },
    );
    this.root.append(heading, list, add);
  }

  /** @param {Record<string, any>} item @param {number} index */
  #row(item, index) {
    const row = document.createElement("div");
    row.className = "settings-lora-row";
    const name = selectField("LoRA", this.available, item.name);
    const model = numberField("Model", item.model_strength, "0.05");
    const clip = numberField("CLIP", item.clip_strength, "0.05");
    name.control.addEventListener(
      "change",
      () => {
        item.name = name.control.value;
      },
      { signal: this.abortController.signal },
    );
    model.control.addEventListener(
      "input",
      () => {
        item.model_strength = Number(model.control.value);
      },
      { signal: this.abortController.signal },
    );
    clip.control.addEventListener(
      "input",
      () => {
        item.clip_strength = Number(clip.control.value);
      },
      { signal: this.abortController.signal },
    );
    row.append(
      name.wrapper,
      model.wrapper,
      clip.wrapper,
      this.#action("↑", index > 0, () => this.#move(index, -1)),
      this.#action("↓", index < this.items.length - 1, () =>
        this.#move(index, 1),
      ),
      this.#action("Entfernen", true, () => this.#remove(index)),
    );
    return row;
  }

  /** @param {string} label @param {boolean} enabled @param {() => void} action */
  #action(label, enabled, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.disabled = !enabled;
    button.addEventListener("click", action, {
      signal: this.abortController.signal,
    });
    return button;
  }

  /** @param {number} index @param {number} direction */
  #move(index, direction) {
    const target = index + direction;
    [this.items[index], this.items[target]] = [
      this.items[target],
      this.items[index],
    ];
    this.#draw();
  }

  /** @param {number} index */
  #remove(index) {
    this.items.splice(index, 1);
    this.#draw();
  }
}

/** @param {string} label @param {string[]} values @param {string} selected */
function selectField(label, values, selected) {
  const wrapper = field(label);
  const control = document.createElement("select");
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    control.append(option);
  }
  control.value = selected;
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label @param {number} value @param {string} step */
function numberField(label, value, step) {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.type = "number";
  control.step = step;
  control.value = String(value);
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "settings-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}
