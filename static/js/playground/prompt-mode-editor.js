import { LoraStackEditor } from "../settings/lora-stack-editor.js";
import { PromptComponentComposer } from "./prompt-component-composer.js";
import { promptKinds } from "./prompt-kind-contract.js";

export { promptKinds } from "./prompt-kind-contract.js";

/** @typedef {Readonly<{kind: string, mode: "fixed" | "random" | "off", componentUid: string | null, revisionUid: string | null, candidateUid: string | null}>} PromptSelectionState */
/** @typedef {{mode?: string, componentUid?: string | null, revisionUid?: string | null, candidateUid?: string | null}} PromptSelectionPatch */
/** @typedef {{kind: string, mode: "fixed" | "random" | "off", component_uid: string | null, revision_uid: string | null, candidate_uid?: string | null}} PromptSelectionValue */
/** @typedef {{selections: PromptSelectionValue[], loras: Array<Record<string, any>>, component_overrides: Array<Record<string, any>>}} PromptModeEditorValue */
/** @typedef {{lora_uid: string, revision_uid: string, model_strength: number, clip_strength: number}} GeneratorStateLora */

/** Own fixed, random and disabled prompt-role controls plus catalog evidence. */
export class PromptModeEditor {
  /** @type {Map<string, PromptSelectionState>} */
  #selectionState = new Map();
  /** @type {Map<string, string | null>} */
  #stableRevisionByComponent = new Map();
  /** @type {Map<string, Record<string, any>>} */
  #componentByUid = new Map();
  /** @type {Map<string, Record<string, any>>} */
  #revisionByIdentity = new Map();

  /** @param {HTMLElement} root @param {() => void} [onChange] @param {{loadComponent?: (uid: string, signal: AbortSignal) => Promise<any>, loadRevisions?: (uid: string, signal: AbortSignal) => Promise<any>, loadGuidance?: (payload: Record<string, any>, signal: AbortSignal) => Promise<any>, materializeCandidate?: (payload: Record<string, any>, signal: AbortSignal) => Promise<any>, onImageSelect?: (url: string) => void}} [evidence] */
  constructor(root, onChange = () => {}, evidence = {}) {
    this.root = root;
    this.abortController = new AbortController();
    this.onChange = typeof onChange === "function" ? onChange : () => {};
    this.loadComponent = evidence.loadComponent || null;
    this.loadRevisions = evidence.loadRevisions || null;
    this.loadGuidance = evidence.loadGuidance || null;
    this.materializeCandidate = evidence.materializeCandidate || null;
    this.onImageSelect = evidence.onImageSelect || (() => {});
    /** @type {Map<string, {mode: HTMLSelectElement, component: HTMLSelectElement, variant: HTMLSelectElement, evidence: HTMLElement, composer: HTMLElement}>} */
    this.rows = new Map();
    /** @type {Map<string, PromptComponentComposer>} */
    this.composers = new Map();
    /** @type {Map<string, Record<string, any>>} */
    this.candidateByUid = new Map();
    /** @type {Map<string, any>} */
    this.cache = new Map();
    /** @type {Map<string, AbortController>} */
    this.requests = new Map();
    /** @type {AbortController | null} */
    this.stateRequest = null;
    this.loras = null;
    this.isBusy = false;
    /** @type {Array<Record<string, any>>} */
    this.loraDefinitions = [];
  }

  /** @param {Array<Record<string, any>>} components @param {Array<Record<string, any>>} [loraDefinitions] */
  render(components, loraDefinitions = []) {
    this.#cancelRequests();
    this.#disposeComposers();
    this.root.replaceChildren();
    this.rows.clear();
    this.#selectionState.clear();
    this.#componentByUid = new Map(
      components.map((component) => [
        String(component.component_uid || ""),
        component,
      ]),
    );
    this.#revisionByIdentity.clear();
    for (const component of components) {
      const componentUid = String(component.component_uid || "");
      for (const revision of [
        component.current_revision,
        component.latest_revision,
      ]) {
        const revisionUid = String(revision?.revision_uid || "");
        if (componentUid && revisionUid)
          this.#revisionByIdentity.set(
            revisionIdentity(componentUid, revisionUid),
            revision,
          );
      }
    }
    this.#stableRevisionByComponent = new Map(
      components.map((component) => [
        String(component.component_uid || ""),
        (component.current_revision || component.latest_revision)?.revision_uid
          ? String(
              (component.current_revision || component.latest_revision)
                .revision_uid,
            )
          : null,
      ]),
    );
    const list = document.createElement("div");
    list.className = "prompt-mode-list";
    for (const [kind, label] of promptKinds) {
      const row = this.#row(kind, label, components);
      list.append(row.element);
      this.rows.set(kind, row.controls);
      this.#transition(
        kind,
        {
          mode: row.controls.mode.value,
          componentUid: row.controls.component.value || null,
        },
        { refresh: false },
      );
      void this.#refresh(kind);
    }
    const loraRoot = document.createElement("section");
    loraRoot.className = "prompt-lora-layer";
    const heading = document.createElement("div");
    heading.className = "prompt-lora-heading";
    const title = document.createElement("h3");
    title.textContent = "LoRAs";
    const note = document.createElement("p");
    note.textContent =
      "Eigene Prompt-Ebene mit Revision, Triggern und getrennten Model-/CLIP-Gewichten.";
    heading.append(title, note);
    const editorRoot = document.createElement("div");
    loraRoot.append(heading, editorRoot);
    this.loraDefinitions = loraDefinitions;
    this.loras?.dispose();
    this.loras = new LoraStackEditor(editorRoot, () => this.onChange());
    this.loras.render([], loraDefinitions);
    this.setBusy(this.isBusy);
    this.root.append(list, loraRoot);
  }

  /** @returns {PromptModeEditorValue} Return the complete API selection intent. */
  value() {
    return {
      selections: promptKinds.map(([kind]) => {
        const selection = this.#selectionState.get(kind);
        const mode = selection?.mode || "random";
        return {
          kind,
          mode,
          component_uid:
            mode === "fixed" ? selection?.componentUid || null : null,
          revision_uid:
            mode === "fixed" ? selection?.revisionUid || null : null,
          candidate_uid:
            mode === "fixed" ? selection?.candidateUid || null : null,
        };
      }),
      loras: this.loras?.value() || [],
      component_overrides: [...this.composers.values()]
        .filter((composer) => composer.isDirty())
        .map((composer) => composer.value()),
    };
  }

  /** @returns {{selections: PromptSelectionValue[], loras: GeneratorStateLora[]}} Return the strict durable-state projection. */
  stateValue() {
    const value = this.value();
    return {
      selections: value.selections,
      loras: value.loras.map((item) => ({
        lora_uid: String(item.lora_uid || ""),
        revision_uid: String(item.revision_uid || ""),
        model_strength: Number(item.model_strength),
        clip_strength: Number(item.clip_strength),
      })),
    };
  }

  /**
   * Restore saved selections after the allowed catalog has rendered.
   * @param {{selections?: PromptSelectionValue[], loras?: Array<Record<string, any>>}} state
   * @returns {Promise<string[]>} Kinds rejected because their mode, component or exact revision is unavailable.
   */
  async applyState(state) {
    const rejected = [];
    const selections = Array.isArray(state.selections) ? state.selections : [];
    this.stateRequest?.abort();
    const controller = new AbortController();
    this.stateRequest = controller;
    const resolvedSelections = new Set();
    await Promise.all(
      selections.map(async (selection) => {
        const kind = String(selection.kind || "");
        const mode = String(selection.mode || "");
        const componentUid = String(selection.component_uid || "");
        const revisionUid = String(selection.revision_uid || "").trim();
        if (mode !== "fixed" || !componentUid || !revisionUid) return;
        try {
          const revision = await this.#resolveRevision(
            componentUid,
            revisionUid,
            controller.signal,
          );
          if (revision) resolvedSelections.add(selection);
          else rejected.push(kind);
        } catch {
          rejected.push(kind);
        }
      }),
    );
    if (this.stateRequest === controller) this.stateRequest = null;
    for (const selection of selections) {
      const kind = String(selection.kind || "");
      const row = this.rows.get(kind);
      if (!row) continue;
      const mode = String(selection.mode || "");
      if (
        !isPromptMode(mode) ||
        ![...row.mode.options].some((option) => option.value === mode)
      ) {
        rejected.push(kind);
        continue;
      }
      const componentUid = String(selection.component_uid || "");
      const revisionUid =
        typeof selection.revision_uid === "string" &&
        selection.revision_uid.trim()
          ? selection.revision_uid.trim()
          : null;
      const candidateUid =
        typeof selection.candidate_uid === "string" &&
        selection.candidate_uid.trim()
          ? selection.candidate_uid.trim()
          : null;
      if (mode === "fixed" && revisionUid && !resolvedSelections.has(selection))
        continue;
      if (
        mode === "fixed" &&
        ![...row.component.options].some(
          (option) => option.value === componentUid,
        )
      ) {
        rejected.push(kind);
        continue;
      }
      this.#transition(
        kind,
        {
          mode,
          componentUid: mode === "fixed" ? componentUid : undefined,
          revisionUid: mode === "fixed" ? revisionUid : null,
          candidateUid: mode === "fixed" ? candidateUid : null,
        },
        {
          refresh: true,
          resetRevisionToLatest: mode === "fixed" && !revisionUid,
        },
      );
    }
    if (this.#applyLoras(state.loras)) rejected.push("loras");
    return rejected;
  }

  /** @param {unknown} loras */
  #applyLoras(loras) {
    if (!Array.isArray(loras)) return false;
    this.loras?.render(loras, this.loraDefinitions);
    return loras.some((requestedLora) => {
      const definition = this.loraDefinitions.find(
        (candidate) => candidate.lora_uid === requestedLora.lora_uid,
      );
      return !definition || definition.available === false;
    });
  }

  /** Show server-resolved random selections after draft creation. @param {Array<Record<string, any>>} components */
  showResolvedComponents(components) {
    for (const component of components || []) {
      const kind = String(component.kind || "");
      const row = this.rows.get(kind);
      if (row?.mode.value === "random")
        void this.#loadInto(kind, String(component.component_uid || ""));
    }
  }

  /** Prevent prompt and LoRA mutations while a draft transition is active. */
  /** @param {boolean} busy */
  setBusy(busy) {
    this.isBusy = busy;
    for (const row of this.rows.values()) {
      row.mode.disabled = busy;
      row.component.disabled = busy || row.mode.value !== "fixed";
      row.variant.disabled = busy || row.mode.value !== "fixed";
    }
    this.loras?.setBusy(busy);
    for (const composer of this.composers.values()) composer.setBusy(busy);
  }

  dispose() {
    this.abortController.abort();
    this.stateRequest?.abort();
    this.stateRequest = null;
    this.#cancelRequests();
    this.loras?.dispose();
    this.loras = null;
    this.#disposeComposers();
    this.rows.clear();
    this.#selectionState.clear();
    this.#stableRevisionByComponent.clear();
    this.#componentByUid.clear();
    this.#revisionByIdentity.clear();
  }

  /** @param {string} kind @param {string} label @param {Array<Record<string, any>>} components */
  #row(kind, label, components) {
    const element = document.createElement("div");
    element.className = "prompt-mode-row";
    element.dataset.kind = kind;
    const title = document.createElement("span");
    title.className = "prompt-kind-label";
    title.textContent = label;
    const mode = document.createElement("select");
    mode.setAttribute("aria-label", `${label}: Modus`);
    mode.append(option("fixed", "fixiert"), option("random", "zufällig"));
    if (kind !== "character") mode.append(option("off", "aus"));
    mode.value = kind === "character" ? "fixed" : "random";
    const component = document.createElement("select");
    component.setAttribute("aria-label", `${label}: Katalogeintrag`);
    for (const item of components.filter((item) => item.kind === kind)) {
      const suffix = item.archived ? " · Archiv" : "";
      component.append(
        option(String(item.component_uid), `${String(item.name)}${suffix}`),
      );
    }
    component.disabled = mode.value !== "fixed";
    const variant = document.createElement("select");
    variant.setAttribute("aria-label", `${label}: Prompt-Variante`);
    variant.append(
      option("stable", "Stabil"),
      option("catalog_candidate", "Katalog-Test"),
      option("calculated", "Rechnerisch"),
      option("next_test", "Nächster Test"),
    );
    variant.disabled = mode.value !== "fixed";
    const evidence = document.createElement("div");
    evidence.className = "prompt-reference";
    const composer = document.createElement("div");
    mode.addEventListener(
      "change",
      () => {
        this.#transition(kind, { mode: mode.value }, { notify: true });
      },
      { signal: this.abortController.signal },
    );
    component.addEventListener(
      "change",
      () => {
        this.#transition(
          kind,
          { componentUid: component.value || null },
          { notify: true },
        );
      },
      { signal: this.abortController.signal },
    );
    variant.addEventListener(
      "change",
      () => void this.#chooseVariant(kind, variant.value),
      { signal: this.abortController.signal },
    );
    element.append(title, mode, component, variant, evidence, composer);
    return {
      element,
      controls: { mode, component, variant, evidence, composer },
    };
  }

  /**
   * Apply one selection transition and synchronize its DOM projection.
   * @param {string} kind
   * @param {PromptSelectionPatch} patch
   * @param {{refresh?: boolean, notify?: boolean, resetRevisionToLatest?: boolean}} [options]
   */
  #transition(kind, patch, options = {}) {
    const row = this.rows.get(kind);
    if (!row) return;
    const previous = this.#selectionState.get(kind);
    const requestedMode =
      patch.mode || previous?.mode || row.mode.value || "random";
    if (!isPromptMode(requestedMode)) return;
    const mode = requestedMode;
    const componentUid =
      patch.componentUid !== undefined
        ? patch.componentUid
        : previous?.componentUid || row.component.value || null;
    const componentChanged = componentUid !== (previous?.componentUid || null);
    const enteredFixed = mode === "fixed" && previous?.mode !== "fixed";
    const stableRevisionUid = componentUid
      ? this.#stableRevisionByComponent.get(componentUid) || null
      : null;
    let revisionUid = null;
    let candidateUid = null;
    if (mode === "fixed") {
      const requestedRevision =
        typeof patch.revisionUid === "string" ? patch.revisionUid.trim() : "";
      revisionUid = requestedRevision
        ? requestedRevision
        : componentChanged || enteredFixed || options.resetRevisionToLatest
          ? stableRevisionUid
          : previous?.revisionUid || stableRevisionUid;
      candidateUid =
        patch.candidateUid !== undefined
          ? patch.candidateUid
          : componentChanged
            ? null
            : previous?.candidateUid || null;
    }
    row.mode.value = mode;
    row.component.value = componentUid || "";
    row.component.disabled = this.isBusy || mode !== "fixed";
    row.variant.disabled = this.isBusy || mode !== "fixed";
    const manualVariant = componentUid
      ? this.#componentByUid.get(componentUid)?.latest_manual_variant
      : null;
    const manualCandidateUid = manualVariant?.candidate_uid || null;
    const selectedCandidate = candidateUid
      ? this.candidateByUid.get(candidateUid)
      : null;
    const manualOption = [...row.variant.options].find(
      (item) => item.value === "catalog_candidate",
    );
    if (manualOption)
      manualOption.disabled =
        !manualCandidateUid && selectedCandidate?.candidate_type !== "manual";
    const existingHistorical = [...row.variant.options].find(
      (item) => item.dataset.historicalRevision === "true",
    );
    existingHistorical?.remove();
    if (candidateUid) {
      row.variant.value =
        candidateUid === manualCandidateUid ||
        selectedCandidate?.candidate_type === "manual"
          ? "catalog_candidate"
          : "calculated";
    } else if (revisionUid && revisionUid !== stableRevisionUid) {
      const historicalRevision = componentUid
        ? this.#revisionByIdentity.get(
            revisionIdentity(componentUid, revisionUid),
          )
        : null;
      const revisionNumber = Number(historicalRevision?.revision_number || 0);
      const historicalOption = option(
        "historical",
        revisionNumber > 0
          ? `Historisch · R${revisionNumber}`
          : "Historische Revision",
      );
      historicalOption.dataset.historicalRevision = "true";
      historicalOption.disabled = true;
      row.variant.append(historicalOption);
      row.variant.value = "historical";
    } else {
      row.variant.value = "stable";
    }
    this.#selectionState.set(
      kind,
      Object.freeze({
        kind,
        mode,
        componentUid,
        revisionUid,
        candidateUid,
      }),
    );
    this.#syncComposer(kind);
    if (options.refresh !== false) void this.#refresh(kind);
    if (options.notify) this.onChange();
  }

  /** @param {string} kind */
  async #refresh(kind) {
    const row = this.rows.get(kind);
    if (!row) return;
    this.requests.get(kind)?.abort();
    if (row.mode.value === "off")
      return renderMessage(row.evidence, "Nicht aktiv");
    if (row.mode.value === "random")
      return renderMessage(row.evidence, "Wird beim Entwurf ausgewählt");
    await this.#loadInto(kind, row.component.value);
  }

  /** @param {string} kind @param {string} variant */
  async #chooseVariant(kind, variant) {
    const row = this.rows.get(kind);
    const selection = this.#selectionState.get(kind);
    if (!row || !selection || selection.mode !== "fixed") return;
    const component = selection.componentUid
      ? this.#componentByUid.get(selection.componentUid)
      : null;
    const stableRevision =
      component?.current_revision || component?.latest_revision;
    const stableRevisionUid = String(stableRevision?.revision_uid || "");
    if (variant === "stable") {
      this.#transition(
        kind,
        { revisionUid: stableRevisionUid, candidateUid: null },
        { notify: true },
      );
      return;
    }
    if (variant === "catalog_candidate") {
      const manualVariant = component?.latest_manual_variant;
      if (manualVariant?.candidate_uid && manualVariant.source_revision_uid) {
        this.#transition(
          kind,
          {
            revisionUid: String(manualVariant.source_revision_uid),
            candidateUid: String(manualVariant.candidate_uid),
          },
          { notify: true, refresh: false },
        );
        row.variant.value = "catalog_candidate";
        return renderMessage(row.evidence, "Katalog-Testkandidat ausgewählt");
      }
      row.variant.value = selection.candidateUid ? "calculated" : "stable";
      return renderMessage(row.evidence, "Kein Katalog-Testkandidat verfügbar");
    }
    if (
      !component ||
      !stableRevision ||
      !stableRevisionUid ||
      !this.loadGuidance ||
      !this.materializeCandidate
    ) {
      row.variant.value = selection.candidateUid ? "calculated" : "stable";
      return renderMessage(row.evidence, "Prompt-Guidance nicht verfügbar");
    }
    this.requests.get(kind)?.abort();
    const controller = new AbortController();
    this.requests.set(kind, controller);
    renderMessage(row.evidence, "Prompt-Guidance wird berechnet …");
    try {
      const request = {
        component_uid: selection.componentUid,
        source_revision_uid: stableRevisionUid,
      };
      const guidance = await this.loadGuidance(request, controller.signal);
      const recommendation =
        variant === "next_test" ? guidance.next_test : guidance.optimized;
      if (!recommendation) {
        row.variant.value = selection.candidateUid ? "calculated" : "stable";
        return renderMessage(
          row.evidence,
          "Noch kein sinnvoller Test ableitbar",
        );
      }
      if (
        variant === "calculated" &&
        JSON.stringify(recommendation.positive_atoms || []) ===
          JSON.stringify(stableRevision.positive_atoms || []) &&
        JSON.stringify(recommendation.negative_atoms || []) ===
          JSON.stringify(stableRevision.negative_atoms || [])
      ) {
        this.#transition(
          kind,
          { revisionUid: stableRevisionUid, candidateUid: null },
          { notify: true, refresh: false },
        );
        row.variant.value = "stable";
        return renderMessage(
          row.evidence,
          "Stabile Variante ist bereits das rechnerische Optimum",
        );
      }
      const candidate = await this.materializeCandidate(
        {
          ...request,
          candidate_type: variant === "next_test" ? "next_test" : "calculated",
          positive_atoms: recommendation.positive_atoms || [],
          negative_atoms: recommendation.negative_atoms || [],
        },
        controller.signal,
      );
      this.candidateByUid.set(String(candidate.candidate_uid || ""), candidate);
      this.#transition(
        kind,
        {
          revisionUid: stableRevisionUid,
          candidateUid: String(candidate.candidate_uid || "") || null,
        },
        { notify: true, refresh: false },
      );
      row.variant.value = variant;
      renderMessage(
        row.evidence,
        variant === "next_test"
          ? "Nächster Test ausgewählt"
          : "Rechnerische Variante ausgewählt",
      );
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        renderMessage(
          row.evidence,
          "Prompt-Guidance konnte nicht geladen werden",
        );
      row.variant.value = selection.candidateUid ? "calculated" : "stable";
    } finally {
      if (this.requests.get(kind) === controller) this.requests.delete(kind);
    }
  }

  /** @param {string} kind @param {string} uid */
  async #loadInto(kind, uid) {
    const row = this.rows.get(kind);
    if (!row || !uid)
      return renderMessage(row?.evidence, "Kein Katalogeintrag gewählt");
    const cached = this.cache.get(uid);
    if (cached) return this.#renderEvidence(row.evidence, cached);
    if (!this.loadComponent)
      return renderMessage(row.evidence, "Referenz nicht verfügbar");
    this.requests.get(kind)?.abort();
    const controller = new AbortController();
    this.requests.set(kind, controller);
    renderMessage(row.evidence, "Referenz wird geladen …");
    try {
      const payload = await this.loadComponent(uid, controller.signal);
      this.cache.set(uid, payload);
      this.#renderEvidence(row.evidence, payload);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError"))
        renderMessage(row.evidence, "Referenz konnte nicht geladen werden");
    } finally {
      if (this.requests.get(kind) === controller) this.requests.delete(kind);
    }
  }

  /** @param {HTMLElement} root @param {Record<string, any>} component */
  #renderEvidence(root, component) {
    root.replaceChildren();
    const images = Array.isArray(component.top_images)
      ? component.top_images
      : [];
    const heading = document.createElement("strong");
    heading.textContent = `${component.name || "Katalogeintrag"} · ${component.kind || ""}`;
    if (!images.length) {
      const empty = document.createElement("span");
      empty.textContent = "Noch kein sichtbares Referenzbild";
      root.append(heading, empty);
      return;
    }
    const image = images[0];
    const button = document.createElement("button");
    button.type = "button";
    button.className = "prompt-reference-image";
    const img = document.createElement("img");
    img.src = String(image.image_url || "");
    img.alt = `Referenz für ${component.name || "Prompt-Baustein"}`;
    button.append(img);
    button.addEventListener(
      "click",
      () => this.onImageSelect(String(image.image_url || "")),
      { signal: this.abortController.signal },
    );
    const meta = document.createElement("span");
    meta.textContent = `${Number(image.average_rating || 0).toFixed(2)} Bewertung · ${Number(image.rating_count || 0)} Belege`;
    root.append(heading, button, meta);
  }

  #cancelRequests() {
    for (const request of this.requests.values()) request.abort();
    this.requests.clear();
  }

  /** @param {string} componentUid @param {string} revisionUid @param {AbortSignal} signal */
  async #resolveRevision(componentUid, revisionUid, signal) {
    const identity = revisionIdentity(componentUid, revisionUid);
    const cached = this.#revisionByIdentity.get(identity);
    if (cached) return cached;
    if (!this.loadRevisions) return null;
    const payload = await this.loadRevisions(componentUid, signal);
    const revisions = Array.isArray(payload?.revisions)
      ? payload.revisions
      : [];
    for (const revision of revisions) {
      const loadedRevisionUid = String(revision.revision_uid || "");
      if (loadedRevisionUid)
        this.#revisionByIdentity.set(
          revisionIdentity(componentUid, loadedRevisionUid),
          revision,
        );
    }
    return this.#revisionByIdentity.get(identity) || null;
  }

  /** @param {string} kind */
  #syncComposer(kind) {
    const row = this.rows.get(kind);
    const selection = this.#selectionState.get(kind);
    this.composers.get(kind)?.dispose();
    this.composers.delete(kind);
    row?.composer.replaceChildren();
    row?.composer.removeAttribute("class");
    if (!row || !selection || selection.mode !== "fixed") return;
    const component = selection.componentUid
      ? this.#componentByUid.get(selection.componentUid)
      : null;
    const stable = component?.current_revision || component?.latest_revision;
    const selectedRevision =
      selection.componentUid && selection.revisionUid
        ? this.#revisionByIdentity.get(
            revisionIdentity(selection.componentUid, selection.revisionUid),
          )
        : null;
    if (
      !component ||
      !stable ||
      !selectedRevision ||
      !selection.componentUid ||
      !selection.revisionUid
    )
      return;
    const candidate = selection.candidateUid
      ? this.candidateByUid.get(selection.candidateUid) ||
        (component.latest_manual_variant?.candidate_uid ===
        selection.candidateUid
          ? component.latest_manual_variant
          : null)
      : null;
    const materializeCandidate = this.materializeCandidate;
    const composer = new PromptComponentComposer(row.composer, {
      kind,
      componentUid: selection.componentUid,
      revisionUid: selection.revisionUid,
      candidateUid: selection.candidateUid,
      positiveAtoms:
        candidate?.positive_atoms || selectedRevision.positive_atoms || [],
      negativeAtoms:
        candidate?.negative_atoms || selectedRevision.negative_atoms || [],
      onChange: () => this.onChange(),
      onReset: () =>
        this.#transition(
          kind,
          {
            revisionUid: String(stable.revision_uid || ""),
            candidateUid: null,
          },
          { notify: true },
        ),
      onSave: materializeCandidate
        ? (payload, signal) => materializeCandidate(payload, signal)
        : undefined,
      onSaved: (saved) => {
        const candidateUid = String(saved.candidate_uid || "");
        if (!candidateUid) return;
        this.candidateByUid.set(candidateUid, saved);
        this.#transition(
          kind,
          { candidateUid },
          { notify: true, refresh: false },
        );
      },
    });
    composer.setBusy(this.isBusy);
    this.composers.set(kind, composer);
  }

  #disposeComposers() {
    for (const composer of this.composers.values()) composer.dispose();
    this.composers.clear();
  }
}

/** @param {HTMLElement | undefined} root @param {string} text */
function renderMessage(root, text) {
  if (!root) return;
  root.replaceChildren();
  const message = document.createElement("span");
  message.textContent = text;
  root.append(message);
}

/** @param {string} value @param {string} label */
function option(value, label) {
  const element = document.createElement("option");
  element.value = value;
  element.textContent = label;
  return element;
}

/** @param {string} value @returns {value is "fixed" | "random" | "off"} */
function isPromptMode(value) {
  return value === "fixed" || value === "random" || value === "off";
}

/** @param {string} componentUid @param {string} revisionUid */
function revisionIdentity(componentUid, revisionUid) {
  return `${componentUid}\u0000${revisionUid}`;
}
