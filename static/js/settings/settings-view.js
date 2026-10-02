import { GenerationProfileEditor } from "./generation-profile-editor.js";

/** Own settings section markup while delegating profile editing. */
export class SettingsView {
  /** @param {HTMLElement} root @param {{onPreferencesSave: (payload: Record<string, any>) => void, onProfileSave: (uid: string | null, payload: Record<string, any>) => void, onProfileArchive: (uid: string, archived: boolean) => void, onProfileDefault: (uid: string) => void, onComfyUiCheck: () => void}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.abortController = new AbortController();
    this.profileEditor = null;
  }

  /** @param {string} section @param {Record<string, any>} data */
  render(section, data) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.profileEditor?.dispose();
    this.profileEditor = null;
    this.root.replaceChildren();
    const container = document.createElement("section");
    container.className = "settings-section";
    if (section === "profiles") this.#profiles(container, data);
    else if (section === "comfyui") this.#comfyUi(container, data.runtime);
    else if (section === "storage") this.#storage(container, data.runtime);
    else this.#preferences(container, section, data);
    this.root.append(container);
  }

  /** Release owned listeners and collaborators. */
  dispose() {
    this.abortController.abort();
    this.profileEditor?.dispose();
    this.root.replaceChildren();
  }

  /** @param {HTMLElement} container @param {Record<string, any>} data */
  #profiles(container, data) {
    container.append(
      heading("Generierungsprofile", "Wiederverwendbare technische Defaults"),
    );
    const list = document.createElement("div");
    list.className = "settings-profile-list";
    for (const profile of /** @type {Array<Record<string, any>>} */ (
      data.generation_profiles || []
    )) {
      const button = actionButton(
        `${profile.name}${profile.is_default ? " · Standard" : ""}${profile.archived ? " · Archiviert" : ""}`,
      );
      button.addEventListener(
        "click",
        () => this.#profileEditor(container, profile, data),
        { signal: this.abortController.signal },
      );
      list.append(button);
    }
    const create = actionButton("Neues Profil");
    create.addEventListener(
      "click",
      () => this.#profileEditor(container, null, data),
      { signal: this.abortController.signal },
    );
    list.append(create);
    const editorRoot = document.createElement("div");
    editorRoot.dataset.profileEditor = "";
    container.append(list, editorRoot);
    const selected = /** @type {Array<Record<string, any>>} */ (
      data.generation_profiles || []
    ).find((/** @type {Record<string, any>} */ profile) => profile.is_default);
    this.#profileEditor(container, selected || null, data);
  }

  /** @param {HTMLElement} container @param {Record<string, any> | null} profile @param {Record<string, any>} data */
  #profileEditor(container, profile, data) {
    const editorRoot = /** @type {HTMLElement} */ (
      container.querySelector("[data-profile-editor]")
    );
    this.profileEditor?.dispose();
    this.profileEditor = new GenerationProfileEditor(editorRoot, {
      onSave: this.actions.onProfileSave,
      onArchive: this.actions.onProfileArchive,
      onDefault: this.actions.onProfileDefault,
    });
    this.profileEditor.render(profile, data.runtime);
  }

  /** @param {HTMLElement} container @param {string} section @param {Record<string, any>} data */
  #preferences(container, section, data) {
    const preferences = data.preferences;
    const titles = {
      general: ["Allgemein", "Darstellung und Standardprofil"],
      review: ["Review", "Sitzungsdefaults ohne neue Rating-Semantik"],
      curation: ["Curation", "Vorhandene kanonische Sets und Reihenfolge"],
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
  }

  /** @param {HTMLElement} container @param {Record<string, any>} runtime */
  #comfyUi(container, runtime) {
    container.append(heading("ComfyUI", "Verbindung und erkannte Fähigkeiten"));
    const status = document.createElement("p");
    status.textContent = runtime.connected ? "Verbunden" : "Nicht verbunden";
    status.dataset.status = runtime.connected ? "completed" : "failed";
    const facts = factList([
      ["Base-URL", runtime.configuration.comfyui_base_url],
      ["Checkpoints", runtime.checkpoints.join(", ") || "Keine erkannt"],
      ["Sampler", runtime.samplers.join(", ") || "Keine erkannt"],
      ["Scheduler", runtime.schedulers.join(", ") || "Keine erkannt"],
      ["LoRAs", runtime.loras.join(", ") || "Keine erkannt"],
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
  if (section === "review") {
    return [
      checkboxField(
        "review_unrated_only",
        "Standardmäßig nur unbewertete Bilder",
        preferences.review_unrated_only,
      ),
      numberField(
        "review_max_attempts",
        "Maximale Kandidatenversuche",
        preferences.review_max_attempts,
        1,
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
      ["comfortable", "compact"],
      preferences.density,
    ),
    selectField(
      "motion",
      "Bewegung",
      ["system", "reduced"],
      preferences.motion,
    ),
    selectField(
      "analytics_page_size",
      "Analytics-Seitengröße",
      [12, 24, 48],
      preferences.analytics_page_size,
      Number,
    ),
    selectField(
      "default_generation_profile_uid",
      "Standardprofil",
      [
        "",
        ...(data.generation_profiles || [])
          .filter(
            (/** @type {Record<string, any>} */ profile) => !profile.archived,
          )
          .map(
            (/** @type {Record<string, any>} */ profile) => profile.profile_uid,
          ),
      ],
      preferences.default_generation_profile_uid || "",
    ),
  ];
}

/** @param {string} name @param {string} label @param {Array<string | number>} values @param {unknown} selected @param {(value: string) => any} [convert] */
function selectField(
  name,
  label,
  values,
  selected,
  convert = (value) => value,
) {
  const wrapper = field(label);
  const control = document.createElement("select");
  for (const value of values) {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value || "Keins");
    control.append(option);
  }
  control.value = String(selected);
  wrapper.append(control);
  return {
    name,
    wrapper,
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

/** @param {string} name @param {string} label @param {unknown} value @param {number} step */
function numberField(name, label, value, step) {
  return textField(
    name,
    label,
    value,
    (input) => Number(input),
    "number",
    String(step),
  );
}

/** @param {string} name @param {string} label @param {unknown} value @param {(value: string) => any} convert @param {string} [type] @param {string} [step] */
function textField(name, label, value, convert, type = "text", step = "") {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.type = type;
  if (step) control.step = step;
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
