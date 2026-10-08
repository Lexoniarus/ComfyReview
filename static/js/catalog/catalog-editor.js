import { PromptAtomEditor } from "../prompts/prompt-atom-editor.js";
import { CatalogEvidenceView } from "./catalog-evidence-view.js";

/** @type {Array<[string, string]>} */
const editableKinds = [
  ["character", "Charakter"],
  ["scene", "Szene"],
  ["atmosphere", "Atmosphäre"],
  ["lighting", "Licht"],
  ["outfit", "Outfit"],
  ["accessory", "Accessoire"],
  ["pose", "Pose"],
  ["expression", "Ausdruck"],
  ["framing", "Bildausschnitt"],
  ["camera_angle", "Kamerawinkel"],
  ["optical_effect", "Optischer Effekt"],
];

/** @type {Array<[string, string]>} */
const contentLevels = [
  ["standard", "Standard"],
  ["sexy", "Sexy"],
  ["lewd", "Lewd"],
  ["nude", "Nude"],
  ["explicit", "Explicit"],
];

/** Own one focused component editor and immutable revision history. */
export class CatalogEditor {
  /** @param {HTMLElement} root @param {{onSave: (payload: Record<string, any>) => void, onArchive: (archived: boolean) => void, onEvidenceOpen: (imageUid: string, imageUrl: string) => void, createGeneratorActions?: (imageUid: string) => HTMLElement}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.abortController = new AbortController();
    this.isBusy = false;
    this.evidence = new CatalogEvidenceView({
      onOpen: actions.onEvidenceOpen,
      createGeneratorActions: actions.createGeneratorActions,
    });
    /** @type {Array<PromptAtomEditor>} */
    this.atomEditors = [];
  }

  /** Render an empty create form. */
  create(catalogKind = "component") {
    if (catalogKind === "lora") this.#renderLoraForm(null, []);
    else this.#renderForm(null, []);
  }

  /** @param {Record<string, any>} component @param {Array<Record<string, any>>} revisions */
  render(component, revisions) {
    if (component.catalog_kind === "lora")
      this.#renderLoraForm(component, revisions);
    else this.#renderForm(component, revisions);
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    this.isBusy = busy;
    for (const control of this.root.querySelectorAll(
      "input, select, textarea, button",
    )) {
      if (
        control instanceof HTMLInputElement ||
        control instanceof HTMLSelectElement ||
        control instanceof HTMLTextAreaElement ||
        control instanceof HTMLButtonElement
      ) {
        control.disabled = busy || control.dataset.locked === "true";
      }
    }
  }

  /** Release owned form listeners. */
  dispose() {
    this.abortController.abort();
    this.#disposeAtomEditors();
    this.evidence.dispose();
  }

  /** @param {Record<string, any> | null} component @param {Array<Record<string, any>>} revisions */
  #renderForm(component, revisions) {
    this.abortController.abort();
    this.#disposeAtomEditors();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "catalog-editor-heading";
    const headingCopy = document.createElement("div");
    const kicker = document.createElement("p");
    kicker.className = "catalog-kicker";
    kicker.textContent = component ? "Editor" : "Neuer Eintrag";
    const title = document.createElement("h2");
    title.textContent = component ? String(component.name) : "Baustein anlegen";
    headingCopy.append(kicker, title);
    heading.append(headingCopy);

    const form = document.createElement("form");
    form.className = "catalog-form";
    const fields = document.createElement("div");
    fields.className = "catalog-fields";
    const kind = selectField("Art", editableKinds, component?.kind || "scene");
    kind.control.dataset.locked = String(Boolean(component));
    const name = textField("Name", component?.name || "");
    const contentLevel = selectField(
      "Inhaltsstufe",
      contentLevels,
      component?.content_level || "standard",
    );
    const tags = textField(
      "Tags, komma-getrennt",
      (component?.tags || []).join(", "),
    );
    const notes = areaField("Notizen", component?.notes || "", false);
    const stableRevision =
      component?.current_revision || component?.latest_revision;
    const positive = new PromptAtomEditor(
      "Positive Atome",
      stableRevision?.positive_atoms || [],
    );
    const negative = new PromptAtomEditor(
      "Negative Atome",
      stableRevision?.negative_atoms || [],
    );
    this.atomEditors = [positive, negative];
    fields.append(
      kind.wrapper,
      name.wrapper,
      contentLevel.wrapper,
      tags.wrapper,
      notes.wrapper,
      positive.element,
      negative.element,
    );
    const snapshots = revisionSnapshots(stableRevision);
    const actions = document.createElement("div");
    actions.className = "catalog-actions";
    const save = document.createElement("button");
    save.type = "submit";
    save.className = "primary-button";
    save.textContent = component ? "Änderung speichern" : "Baustein anlegen";
    actions.append(save);
    if (component) {
      const archive = document.createElement("button");
      archive.type = "button";
      archive.className = "archive-button";
      archive.textContent = component.archived
        ? "Wiederherstellen"
        : "Archivieren";
      archive.addEventListener(
        "click",
        () => this.actions.onArchive(!component.archived),
        { signal: this.abortController.signal },
      );
      actions.append(archive);
    }
    form.append(fields, snapshots, actions);
    form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        this.actions.onSave({
          kind: kind.control.value,
          name: name.control.value,
          content_level: contentLevel.control.value,
          tags: nameList(tags.control.value),
          notes: notes.control.value,
          positive_atoms: positive.value(),
          negative_atoms: negative.value(),
        });
      },
      { signal: this.abortController.signal },
    );
    if (component) {
      this.evidence.render(component.top_images || []);
      this.root.append(heading, this.evidence.element, form);
    } else {
      this.root.append(heading, form);
    }
    if (component) this.root.append(revisionHistory(revisions));
    this.setBusy(this.isBusy);
  }

  #disposeAtomEditors() {
    for (const editor of this.atomEditors) editor.dispose();
    this.atomEditors = [];
  }

  /** @param {Record<string, any> | null} lora @param {Array<Record<string, any>>} revisions */
  #renderLoraForm(lora, revisions) {
    this.abortController.abort();
    this.#disposeAtomEditors();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "catalog-editor-heading";
    const copy = document.createElement("div");
    const kicker = document.createElement("p");
    kicker.className = "catalog-kicker";
    kicker.textContent = "LoRA-Katalog";
    const title = document.createElement("h2");
    title.textContent = lora ? String(lora.display_name) : "LoRA anlegen";
    copy.append(kicker, title);
    heading.append(copy);

    const form = document.createElement("form");
    form.className = "catalog-form";
    const fields = document.createElement("div");
    fields.className = "catalog-fields";
    const displayName = textField("Name", lora?.display_name || "");
    const providerName = textField(
      "ComfyUI-Dateiname",
      lora?.provider_name || "",
    );
    providerName.control.required = true;
    const contentLevel = selectField(
      "Inhaltsstufe",
      contentLevels,
      lora?.latest_revision?.content_level || "standard",
    );
    const tags = textField(
      "Tags, komma-getrennt",
      (lora?.tags || []).join(", "),
    );
    const notes = areaField("Notizen", lora?.notes || "", false);
    const modelWeight = numberField(
      "Standardgewicht Model",
      lora?.latest_revision?.default_model_strength ?? 1,
    );
    const clipWeight = numberField(
      "Standardgewicht CLIP",
      lora?.latest_revision?.default_clip_strength ?? 1,
    );
    const positive = new PromptAtomEditor(
      "Positive Trigger-Atome",
      lora?.latest_revision?.positive_atoms || [],
    );
    const negative = new PromptAtomEditor(
      "Negative Trigger-Atome",
      lora?.latest_revision?.negative_atoms || [],
    );
    this.atomEditors = [positive, negative];
    fields.append(
      displayName.wrapper,
      providerName.wrapper,
      contentLevel.wrapper,
      tags.wrapper,
      notes.wrapper,
      modelWeight.wrapper,
      clipWeight.wrapper,
      positive.element,
      negative.element,
    );
    const actions = document.createElement("div");
    actions.className = "catalog-actions";
    const save = document.createElement("button");
    save.type = "submit";
    save.className = "primary-button";
    save.textContent = lora ? "Änderung speichern" : "LoRA anlegen";
    actions.append(save);
    if (lora) {
      const archive = document.createElement("button");
      archive.type = "button";
      archive.className = "archive-button";
      archive.textContent = lora.archived ? "Wiederherstellen" : "Archivieren";
      archive.addEventListener(
        "click",
        () => this.actions.onArchive(!lora.archived),
        { signal: this.abortController.signal },
      );
      actions.append(archive);
    }
    form.append(fields, actions);
    form.addEventListener(
      "submit",
      (event) => {
        event.preventDefault();
        this.actions.onSave({
          catalog_kind: "lora",
          provider_name: providerName.control.value,
          display_name: displayName.control.value,
          content_level: contentLevel.control.value,
          tags: nameList(tags.control.value),
          notes: notes.control.value,
          default_model_strength: Number(modelWeight.control.value),
          default_clip_strength: Number(clipWeight.control.value),
          positive_atoms: positive.value(),
          negative_atoms: negative.value(),
          expected_revision: Number(lora?.revision || 1),
        });
      },
      { signal: this.abortController.signal },
    );
    this.root.append(heading, form);
    if (lora) this.root.append(revisionHistory(revisions));
    this.setBusy(this.isBusy);
  }
}

/** @param {string} label @param {Array<[string, string]>} values @param {string} selected */
function selectField(label, values, selected) {
  const wrapper = field(label);
  const control = document.createElement("select");
  for (const [value, text] of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    control.append(option);
  }
  control.value = selected;
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label @param {string} value */
function textField(label, value) {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.value = value;
  control.required = label === "Name";
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label @param {number} value */
function numberField(label, value) {
  const wrapper = field(label);
  const control = document.createElement("input");
  control.type = "number";
  control.step = "0.01";
  control.value = String(value);
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label @param {string} value @param {boolean} prompt */
function areaField(label, value, prompt) {
  const wrapper = field(label);
  const control = document.createElement("textarea");
  control.value = value;
  if (!prompt) control.style.minHeight = "5rem";
  wrapper.append(control);
  return { wrapper, control };
}

/** @param {string} label */
function field(label) {
  const wrapper = document.createElement("label");
  wrapper.className = "catalog-field";
  wrapper.append(document.createTextNode(label));
  return wrapper;
}

/** @param {string} value */
function nameList(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

/** @param {Array<Record<string, any>>} revisions */
function revisionHistory(revisions) {
  const history = document.createElement("section");
  history.className = "catalog-history";
  const title = document.createElement("h3");
  title.textContent = "Revisionshistorie";
  history.append(title);
  for (const revision of [...revisions].reverse()) {
    const details = document.createElement("details");
    details.className = "catalog-revision";
    const summary = document.createElement("summary");
    summary.textContent = `Revision ${revision.revision_number}`;
    const positive = document.createElement("pre");
    positive.textContent = atomSummary("Positiv", revision.positive_atoms);
    const negative = document.createElement("pre");
    negative.textContent = atomSummary("Negativ", revision.negative_atoms);
    details.append(summary, positive, negative);
    history.append(details);
  }
  return history;
}

/** @param {string} label @param {unknown} values */
function atomSummary(label, values) {
  const atoms = Array.isArray(values) ? values : [];
  const lines = atoms.map(
    (atom) => `${String(atom.text || "")} · ${Number(atom.weight ?? 1)}`,
  );
  return `${label}\n${lines.join("\n") || "—"}`;
}

/** @param {Record<string, any> | undefined} revision */
function revisionSnapshots(revision) {
  const section = document.createElement("section");
  section.className = "catalog-rendered-snapshots";
  const title = document.createElement("h3");
  title.textContent = "Gespeicherter Render-Snapshot";
  section.append(title);
  for (const [label, value] of [
    ["Positiv", revision?.positive_text],
    ["Negativ", revision?.negative_text],
  ]) {
    const heading = document.createElement("h4");
    heading.textContent = label;
    const snapshot = document.createElement("pre");
    snapshot.textContent = String(value || "—");
    section.append(heading, snapshot);
  }
  return section;
}
