const parameterLabels = {
  checkpoint: "Checkpoint",
  sampler: "Sampler",
  scheduler: "Scheduler",
  steps: "Steps",
  cfg: "CFG",
  denoise: "Denoise",
};

/** Present server-calculated render evidence and explicit apply actions. */
export class RenderGuidancePanel {
  /** @param {HTMLElement} root @param {{onApplySetup?: (settings: Record<string, any>) => void, onApplyParameter?: (parameter: string, value: string) => void, onModeChange?: (basis: "observed" | "predicted", scope: "setup" | "parameter") => void}} [callbacks] */
  constructor(root, callbacks = {}) {
    this.root = root;
    this.onApplySetup = callbacks.onApplySetup || (() => {});
    this.onApplyParameter = callbacks.onApplyParameter || (() => {});
    this.onModeChange = callbacks.onModeChange || (() => {});
    /** @type {"observed" | "predicted"} */
    this.basis = "observed";
    /** @type {"setup" | "parameter"} */
    this.scope = "setup";
    this.payload = null;
    this.abortController = new AbortController();
    this.#bind();
  }

  /** @param {Record<string, any>} payload */
  render(payload) {
    this.payload = payload;
    this.#renderBody();
  }

  /** @param {string} message */
  renderLoading(message = "Evidenz wird berechnet …") {
    const body = this.root.querySelector("[data-guidance-body]");
    if (body instanceof HTMLElement) body.replaceChildren(messageNode(message));
  }

  dispose() {
    this.abortController.abort();
  }

  #bind() {
    this.root.replaceChildren();
    const header = document.createElement("div");
    header.className = "guidance-header";
    const title = document.createElement("div");
    const heading = document.createElement("h3");
    heading.textContent = "Evidenzbasierte Hilfe";
    const explanation = document.createElement("p");
    explanation.className = "guidance-description";
    explanation.textContent =
      "Empfehlungen ändern nichts, bis du sie ausdrücklich übernimmst.";
    title.append(heading, explanation);
    const switches = document.createElement("div");
    switches.className = "guidance-switches";
    switches.append(
      segmented(
        "Grundlage",
        "guidance-basis",
        [
          ["observed", "Gesichtet"],
          ["predicted", "Rechnerisch"],
        ],
        this.basis,
      ),
      segmented(
        "Ebene",
        "guidance-scope",
        [
          ["setup", "Gesamtsetup"],
          ["parameter", "Einzelwerte"],
        ],
        this.scope,
      ),
    );
    const body = document.createElement("div");
    body.dataset.guidanceBody = "";
    header.append(title, switches);
    this.root.append(header, body);
    this.root.addEventListener(
      "change",
      (event) => {
        if (!(event.target instanceof HTMLInputElement)) return;
        if (event.target.name === "guidance-basis")
          this.basis =
            event.target.value === "predicted" ? "predicted" : "observed";
        if (event.target.name === "guidance-scope")
          this.scope =
            event.target.value === "parameter" ? "parameter" : "setup";
        this.#renderBody();
        this.onModeChange(this.basis, this.scope);
      },
      { signal: this.abortController.signal },
    );
    this.root.addEventListener("click", this.#handleClick.bind(this), {
      signal: this.abortController.signal,
    });
  }

  /** @param {Event} event */
  #handleClick(event) {
    const button =
      event.target instanceof Element
        ? event.target.closest("button[data-guidance-action]")
        : null;
    if (!(button instanceof HTMLButtonElement) || !this.payload) return;
    if (button.dataset.guidanceAction === "setup") {
      const recommendation = this.#recommendation();
      if (recommendation?.applicable)
        this.onApplySetup(recommendation.settings);
      return;
    }
    if (button.dataset.guidanceAction === "parameter")
      this.#applyParameter(button);
  }

  /** @param {HTMLButtonElement} button */
  #applyParameter(button) {
    const parameter = String(button.dataset.parameter);
    const value = String(button.dataset.value);
    this.onApplyParameter(parameter, value);
  }

  #renderBody() {
    const body = this.root.querySelector("[data-guidance-body]");
    if (!(body instanceof HTMLElement)) return;
    body.replaceChildren();
    if (!this.payload) {
      body.append(messageNode("Noch keine Evidenz geladen."));
      return;
    }
    body.append(this.#currentSummary());
    if (this.scope === "setup") body.append(this.#setupCard());
    else body.append(this.#parameterList());
  }

  #currentSummary() {
    const current = this.payload?.current?.[this.basis];
    const element = document.createElement("p");
    element.className = "guidance-current";
    if (!current?.evidence) {
      element.textContent =
        "Das aktuelle Setup ist in dieser Grundlage nicht belastbar bewertbar.";
      return element;
    }
    const evidence = current.evidence;
    const provenance = evidence.jointly_observed
      ? "gemeinsam getestet"
      : this.basis === "predicted"
        ? "prognostiziert"
        : "nur teilweise belegt";
    element.textContent = `Aktuelles Setup: ${provenance} · ${formatScore(evidence)} · ${supportText(evidence)}`;
    setTone(element, evidence, this.basis);
    return element;
  }

  #setupCard() {
    const recommendation = this.#recommendation();
    if (!recommendation)
      return messageNode(
        "Für diesen Modus gibt es noch keine belastbare Empfehlung.",
      );
    const card = document.createElement("article");
    card.className = "guidance-recommendation";
    setTone(card, recommendation.evidence, this.basis);
    const heading = document.createElement("h4");
    heading.textContent =
      this.basis === "observed"
        ? "Stabilstes geprüftes Setup"
        : "Beste prognostizierte Kombination";
    const settings = document.createElement("p");
    settings.className = "guidance-detail";
    settings.textContent = settingsText(recommendation.settings);
    const evidence = document.createElement("p");
    evidence.className = "guidance-detail";
    evidence.textContent = `${formatScore(recommendation.evidence)} · ${supportText(recommendation.evidence)}`;
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.guidanceAction = "setup";
    button.disabled = !recommendation.applicable;
    button.textContent = recommendation.applicable
      ? "Gesamtsetup übernehmen"
      : "Derzeit nicht in ComfyUI verfügbar";
    card.append(heading, settings, evidence, button);
    return card;
  }

  #parameterList() {
    const list = document.createElement("div");
    list.className = "guidance-parameters";
    const recommendation = this.#recommendation();
    if (!recommendation) {
      list.append(
        messageNode(
          "Für Einzelwerte gibt es noch keine belastbare Empfehlung.",
        ),
      );
      return list;
    }
    for (const [parameter, label] of Object.entries(parameterLabels)) {
      const value = String(recommendation.settings?.[parameter] ?? "");
      const payload = this.payload || {};
      const parameterValues = Array.isArray(payload.parameter_values)
        ? payload.parameter_values
        : [];
      const detail = parameterValues.find(
        (/** @type {Record<string, any>} */ item) =>
          item.parameter === parameter && String(item.value) === value,
      );
      const evidence = detail?.[this.basis];
      const row = document.createElement("article");
      row.className = "guidance-parameter";
      if (evidence) setTone(row, evidence, this.basis);
      const name = document.createElement("strong");
      name.textContent = `${label}: ${value}`;
      const status = document.createElement("span");
      status.className = "guidance-parameter-status";
      status.textContent = evidence
        ? `${formatScore(evidence)} · ${supportText(evidence)}`
        : "nicht ausreichend belegt";
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.guidanceAction = "parameter";
      button.dataset.parameter = parameter;
      button.dataset.value = value;
      button.disabled = detail
        ? !detail.applicable
        : !recommendation.applicable;
      button.textContent = "Übernehmen";
      row.append(name, status, button);
      list.append(row);
    }
    return list;
  }

  #recommendation() {
    const responseScope = this.scope === "parameter" ? "parameters" : "setup";
    return (
      this.payload?.recommendations?.[`${this.basis}_${responseScope}`] || null
    );
  }
}

/** @param {string} label @param {string} name @param {Array<[string, string]>} values @param {string} selected */
function segmented(label, name, values, selected) {
  const group = document.createElement("fieldset");
  group.className = "segmented-control";
  const legend = document.createElement("legend");
  legend.textContent = label;
  group.append(legend);
  for (const [value, text] of values) {
    const wrapper = document.createElement("label");
    const input = document.createElement("input");
    input.type = "radio";
    input.name = name;
    input.value = value;
    input.checked = value === selected;
    const span = document.createElement("span");
    span.textContent = text;
    wrapper.append(input, span);
    group.append(wrapper);
  }
  return group;
}

/** @param {string} text */
function messageNode(text) {
  const element = document.createElement("p");
  element.className = "guidance-empty";
  element.textContent = text;
  return element;
}

/** @param {HTMLElement} element @param {Record<string, any>} evidence @param {string} basis */
function setTone(element, evidence, basis) {
  const rank =
    evidence.relative_rank == null
      ? Number.NaN
      : Number(evidence.relative_rank);
  element.dataset.tone = Number.isFinite(rank)
    ? rank >= 0.67
      ? "high"
      : rank >= 0.34
        ? "medium"
        : "low"
    : "neutral";
  element.dataset.source = basis;
}

/** @param {Record<string, any>} evidence */
function formatScore(evidence) {
  const score = Number(evidence.expected_success_rate) * 100;
  return Number.isFinite(score)
    ? `${score.toFixed(1)} % erwarteter Erfolg`
    : "ohne Qualitätswert";
}

/** @param {Record<string, any>} evidence */
function supportText(evidence) {
  return `${Number(evidence.image_count || 0)} Bilder · ${Number(evidence.review_count || 0)} Reviews · ${confidenceLabel(evidence.confidence)}`;
}

/** @param {string} confidence */
function confidenceLabel(confidence) {
  return (
    {
      insufficient: "nicht belastbar",
      low: "geringe Evidenz",
      medium: "mittlere Sicherheit",
      high: "hohe Sicherheit",
    }[confidence] || "unbekannt"
  );
}

/** @param {Record<string, any>} settings */
function settingsText(settings) {
  return Object.entries(parameterLabels)
    .map(([key, label]) => `${label} ${settings?.[key] ?? "–"}`)
    .join(" · ");
}
