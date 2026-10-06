/** Own an ordered editable LoRA stack and its DOM lifecycle. */
export class LoraStackEditor {
  /** @param {HTMLElement} root @param {() => void} [onChange] */
  constructor(root, onChange = () => {}) {
    this.root = root;
    this.onChange = onChange;
    /** @type {Array<Record<string, any>>} */
    this.available = [];
    /** @type {Array<Record<string, any>>} */
    this.items = [];
    this.abortController = new AbortController();
  }

  /** @param {Array<Record<string, any>>} items @param {Array<string | Record<string, any>>} available */
  render(items, available) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.available = available.map((item) =>
      typeof item === "string"
        ? { name: item, lora_uid: null, content_level: null }
        : {
            name: String(item.provider_name || item.name || ""),
            display_name: String(
              item.display_name || item.provider_name || item.name || "",
            ),
            lora_uid: item.lora_uid || null,
            revision_uid: item.latest_revision?.revision_uid || null,
            default_model_strength: Number(
              item.latest_revision?.default_model_strength ?? 1,
            ),
            default_clip_strength: Number(
              item.latest_revision?.default_clip_strength ?? 1,
            ),
            content_level: item.content_level || null,
            available: item.available !== false,
          },
    );
    this.items = items.map((item) => ({
      name: String(item.provider_name || item.name || ""),
      model_strength: Number(item.model_strength ?? 1),
      clip_strength: Number(item.clip_strength ?? 1),
      lora_uid: item.lora_uid || null,
      revision_uid: item.revision_uid || null,
      content_level: item.content_level || null,
    }));
    this.#draw();
  }

  /** Return the ordered browser draft. */
  value() {
    return this.items.map((item) => ({
      name: item.name,
      model_strength: item.model_strength,
      clip_strength: item.clip_strength,
      lora_uid: item.lora_uid,
      revision_uid: item.revision_uid,
    }));
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
          (candidate) =>
            candidate.available !== false &&
            !this.items.some((item) => item.name === candidate.name),
        );
        if (!selected) return;
        this.items.push({
          name: selected.name,
          model_strength: selected.default_model_strength ?? 1,
          clip_strength: selected.default_clip_strength ?? 1,
          lora_uid: selected.lora_uid,
          revision_uid: selected.revision_uid,
          content_level: selected.content_level,
        });
        this.#draw();
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    this.root.append(heading, list, add);
  }

  /** @param {Record<string, any>} item @param {number} index */
  #row(item, index) {
    const row = document.createElement("div");
    row.className = "settings-lora-row";
    const known = this.available.find(
      (candidate) => candidate.name === item.name,
    );
    const candidates = known
      ? this.available
      : [
          ...this.available,
          {
            name: item.name,
            display_name: `${item.name} · nicht verfügbar`,
            available: false,
          },
        ];
    const name = selectField("LoRA", candidates, item.name);
    const selectedAvailable = Boolean(known && known.available !== false);
    row.dataset.availability = selectedAvailable ? "available" : "missing";
    if (!selectedAvailable) {
      const warning = document.createElement("span");
      warning.className = "settings-lora-warning";
      warning.textContent = "Provider-Datei nicht verfügbar";
      row.append(warning);
    }
    const model = numberField("Model", item.model_strength, "0.05");
    const clip = numberField("CLIP", item.clip_strength, "0.05");
    name.control.addEventListener(
      "change",
      () => {
        item.name = name.control.value;
        const selected = this.available.find(
          (candidate) => candidate.name === item.name,
        );
        item.lora_uid = selected?.lora_uid || null;
        item.revision_uid = selected?.revision_uid || null;
        item.content_level = selected?.content_level || null;
        item.model_strength = selected?.default_model_strength ?? 1;
        item.clip_strength = selected?.default_clip_strength ?? 1;
        model.control.value = String(item.model_strength);
        clip.control.value = String(item.clip_strength);
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    model.control.addEventListener(
      "input",
      () => {
        item.model_strength = Number(model.control.value);
        this.onChange();
      },
      { signal: this.abortController.signal },
    );
    clip.control.addEventListener(
      "input",
      () => {
        item.clip_strength = Number(clip.control.value);
        this.onChange();
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
    this.onChange();
  }

  /** @param {number} index */
  #remove(index) {
    this.items.splice(index, 1);
    this.#draw();
    this.onChange();
  }
}

/** @param {string} label @param {Array<Record<string, any>>} values @param {string} selected */
function selectField(label, values, selected) {
  const wrapper = field(label);
  const control = document.createElement("select");
  for (const value of values) {
    const option = document.createElement("option");
    option.value = String(value.name || "");
    option.textContent = String(value.display_name || value.name || "");
    option.disabled = value.available === false && option.value !== selected;
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
