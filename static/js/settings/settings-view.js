/** Own settings section markup and focused runtime views. */
export class SettingsView {
  /** @param {HTMLElement} root @param {{onPreferencesSave: (payload: Record<string, any>) => void, onComfyUiCheck: () => void, onLoraClassify: (providerName: string, contentLevel: string) => void, onLoraPreview: (uid: string) => void, onLoraApply: (uid: string, revision: number) => void}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.abortController = new AbortController();
  }

  /** @param {string} section @param {Record<string, any>} data */
  render(section, data) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    const container = document.createElement("section");
    container.className = "settings-section";
    if (section === "comfyui") this.#comfyUi(container, data.runtime);
    else if (section === "storage") this.#storage(container, data.runtime);
    else this.#preferences(container, section, data);
    this.root.append(container);
  }

  /** Release owned listeners and collaborators. */
  dispose() {
    this.abortController.abort();
    this.root.replaceChildren();
  }

  /** @param {HTMLElement} container @param {string} section @param {Record<string, any>} data */
  #preferences(container, section, data) {
    const preferences = data.preferences;
    const titles = {
      general: ["Allgemein", "Darstellung und Analyseumfang"],
      review: ["Review", "Sitzungsdefaults ohne neue Rating-Semantik"],
      curation: ["Curation", "Vorhandene kanonische Sets und Reihenfolge"],
      content: [
        "Inhaltsstufen",
        "Freigegebene NSFW-Stufen nach Character-Chronicles-Semantik",
      ],
    };
    const titleKey = /** @type {keyof typeof titles} */ (
      section in titles ? section : "general"
    );
    const [title, subtitle] = titles[titleKey];
    container.append(heading(title, subtitle));
    const form = document.createElement("form");
    form.className = "settings-form";
    const grid = document.createElement("div");
    grid.className = "settings-form-grid";
    const fields = preferenceFields(section, preferences, data);
    for (const descriptor of fields) grid.append(descriptor.wrapper);
    const save = actionButton("Speichern");
    save.type = "submit";
    form.append(grid, save);
    form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        const update = { ...preferences };
        for (const descriptor of fields) {
          update[descriptor.name] = descriptor.read();
        }
        this.actions.onPreferencesSave(update);
      },
      { signal: this.abortController.signal },
    );
    container.append(form);
    if (section === "content") this.#loraPolicies(container, data);
  }

  /** @param {HTMLElement} container @param {Record<string, any>} data */
  #loraPolicies(container, data) {
    container.append(
      heading(
        "LoRA-Status",
        "Bearbeitung, Trigger und Standardgewichte liegen ausschließlich im Katalog.",
      ),
    );
    const catalogLink = document.createElement("a");
    catalogLink.className = "secondary-button";
    catalogLink.href = "/catalog";
    catalogLink.textContent = "LoRA-Katalog öffnen";
    container.append(catalogLink);
    const definitions = new Map(
      (data.lora_definitions || []).map(
        (/** @type {Record<string, any>} */ item) => [item.provider_name, item],
      ),
    );
    const names = [
      ...new Set([...(data.runtime?.loras || []), ...definitions.keys()]),
    ].sort((left, right) => left.localeCompare(right));
    const list = document.createElement("div");
    list.className = "settings-lora-list";
    for (const name of names) {
      const definition = definitions.get(name) || null;
      const row = document.createElement("div");
      row.className = "settings-lora-row";
      const title = document.createElement("strong");
      title.textContent = name;
      const level = document.createElement("span");
      level.className = "settings-lora-status";
      level.textContent = definition?.content_level || "Nicht eingestuft";
      row.dataset.classification = definition?.content_level
        ? "classified"
        : "unclassified";
      row.append(title, level);
      list.append(row);
    }
    container.append(list);
  }

  /** @param {HTMLElement} container @param {Record<string, any>} runtime */
  #comfyUi(container, runtime) {
    container.append(heading("ComfyUI", "Verbindung und erkannte Fähigkeiten"));
    const status = document.createElement("p");
    status.textContent = runtime.connected
      ? "Verbunden"
      : runtime.message === "cached"
        ? "Nicht live geprüft · letzte Erkennung"
        : runtime.message === "not_checked"
          ? "Noch nicht geprüft"
          : "Nicht verbunden";
    status.dataset.status = runtime.connected ? "completed" : "failed";
    const facts = factList([
      ["Base-URL", runtime.configuration.comfyui_base_url],
      ["Checkpoints", runtime.checkpoints.join(", ") || "Keine erkannt"],
      ["Sampler", runtime.samplers.join(", ") || "Keine erkannt"],
      ["Scheduler", runtime.schedulers.join(", ") || "Keine erkannt"],
      ["LoRAs", runtime.loras.join(", ") || "Keine erkannt"],
      [
        "Upscaler",
        runtime.upscale_models?.join(", ") || "Kein Upscaler erkannt",
      ],
    ]);
    const check = actionButton("Verbindung testen");
    check.addEventListener("click", this.actions.onComfyUiCheck, {
      signal: this.abortController.signal,
    });
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent =
      "Änderungen an Base-URL oder Environment erfolgen außerhalb des Browsers und benötigen einen Neustart.";
    container.append(status, facts, check, note);
  }

  /** @param {HTMLElement} container @param {Record<string, any>} runtime */
  #storage(container, runtime) {
    container.append(
      heading("Speicher und Datenbank", "Read-only Runtime-Konfiguration"),
    );
    const configuration = runtime.configuration;
    container.append(
      factList([
        ["Output", configuration.output_root],
        ["Workflows", configuration.workflows_directory],
        ["Canonical DB", configuration.canonical_database_path],
        ["Schema", `v${configuration.schema_version}`],
        ["Runtime", configuration.runtime_mode],
        ["Environment", configuration.environment_variables.join(", ")],
      ]),
    );
  }
}

/** @param {string} section @param {Record<string, any>} preferences @param {Record<string, any>} data */
function preferenceFields(section, preferences, data) {
  if (section === "content") {
    return [contentLevelField(preferences.enabled_content_levels || [])];
  }
  if (section === "review") {
    return [
      checkboxField(
        "review_prioritize_unrated",
        "Unbewertete Bilder priorisieren",
        preferences.review_prioritize_unrated,
      ),
    ];
  }
  if (section === "curation") {
    return [
      selectField(
        "default_curation_set_key",
        "Standard-Set",
        ["", ...data.curation_set_keys],
        preferences.default_curation_set_key || "",
      ),
      textField(
        "curation_set_order",
        "Sichtbare Reihenfolge (Komma-getrennt)",
        preferences.curation_set_order.join(", "),
        (value) =>
          value
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
      ),
    ];
  }
  return [
    selectField(
      "density",
      "Dichte",
      [
        { value: "comfortable", label: "Komfortabel" },
        { value: "compact", label: "Kompakt" },
      ],
      preferences.density,
    ),
    selectField(
      "motion",
      "Bewegung",
      [
        { value: "system", label: "Systemvorgabe" },
        { value: "reduced", label: "Reduziert" },
      ],
      preferences.motion,
    ),
    selectField(
      "analytics_page_size",
      "Analytics-Seitengröße",
      [12, 24, 48],
      preferences.analytics_page_size,
      Number,
    ),
  ];
}

/** @param {Array<string>} selected */
function contentLevelField(selected) {
  const wrapper = document.createElement("fieldset");
  wrapper.className = "settings-content-levels";
  const legend = document.createElement("legend");
  legend.textContent = "Erlaubte Inhaltsstufen";
  wrapper.append(legend);
  /** @type {Array<HTMLInputElement>} */
  const controls = [];
  for (const [value, label] of [
    ["standard", "Standard"],
    ["sexy", "Sexy"],
    ["lewd", "Lewd"],
    ["nude", "Nude"],
    ["explicit", "Explicit"],
  ]) {
    const row = document.createElement("label");
    const control = document.createElement("input");
    control.type = "checkbox";
    control.value = value;
    control.checked = value === "standard" || selected.includes(value);
    control.disabled = value === "standard";
    row.append(control, document.createTextNode(label));
    wrapper.append(row);
    controls.push(control);
  }
  return {
    name: "enabled_content_levels",
    wrapper,
    read: () =>
      controls
        .filter((control) => control.checked)
        .map((control) => control.value),
  };
}

/** @typedef {{value: string | number, label: string}} SelectOption */

/** @param {string} name @param {string} label @param {Array<string | number | SelectOption>} values @param {unknown} selected @param {(value: string) => any} [convert] */
function selectField(
  name,
  label,
  values,
  selected,
  convert = (value) => value,
) {
  const wrapper = field(label);
  const control = document.createElement("select");
  for (const item of values) {
    const value = typeof item === "object" ? item.value : item;
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent =
      typeof item === "object" ? item.label : String(value || "Keins");
    control.append(option);
  }
  control.value = String(selected);
  wrapper.append(control);
  return {
    name,
    wrapper,
    control,
    read: () => (control.value ? convert(control.value) : null),
  };
}

/** @param {string} name @param {string} label @param {unknown} checked */
function checkboxField(name, label, checked) {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.type = "checkbox";
  control.checked = Boolean(checked);
  wrapper.append(control);
  return { name, wrapper, read: () => control.checked };
}

/** @param {string} name @param {string} label @param {unknown} value @param {(value: string) => any} convert */
function textField(name, label, value, convert) {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.type = "text";
  control.value = String(value ?? "");
  wrapper.append(control);
  return { name, wrapper, read: () => convert(control.value) };
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "settings-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}

/** @param {string} title @param {string} subtitle */
function heading(title, subtitle) {
  const wrapper = document.createElement("header");
  const kicker = document.createElement("p");
  kicker.className = "settings-section-kicker";
  kicker.textContent = "Einstellungen";
  const headingElement = document.createElement("h2");
  headingElement.textContent = title;
  const description = document.createElement("p");
  description.className = "muted";
  description.textContent = subtitle;
  wrapper.append(kicker, headingElement, description);
  return wrapper;
}

/** @param {Array<[string, unknown]>} items */
function factList(items) {
  const list = document.createElement("dl");
  list.className = "settings-facts";
  for (const [label, value] of items) {
    const row = document.createElement("div");
    row.className = "settings-fact";
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = String(value);
    row.append(term, detail);
    list.append(row);
  }
  return list;
}

/** @param {string} label */
function actionButton(label) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  return button;
}
