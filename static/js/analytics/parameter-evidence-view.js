import {
  emptyMessage,
  parameterLabels,
  recordValue,
  reportIntro,
  textValue,
} from "./analytics-formatters.js";
import { AnalyticsCardRail } from "./analytics-card-rail.js";
import { createGeneratorHandoffAction } from "../playground/generator-handoff-action.js";
import {
  analyticsActionGroup,
  createBestImagePromptAction,
} from "./best-image-prompt-action.js";

/** Render the same four evidence modes exposed by the Generator. */
export class ParameterEvidenceView {
  /** @param {{images: import("./evidence-image-strip.js").EvidenceImageStrip}} dependencies */
  constructor(dependencies) {
    this.images = dependencies.images;
    this.rail = new AnalyticsCardRail("analytics-guidance-grid");
    this.collection = this.rail.track;
  }

  /** @param {HTMLElement} root @param {Record<string, any>} payload */
  render(root, payload) {
    this.rail.clear();
    const basis = String(payload.basis || "observed");
    const scope = String(payload.scope || "setup");
    const parameter = String(payload.parameter || "sampler");
    root.append(
      reportIntro(
        "Render-Analyse",
        "Gesichtete Stabilität und rechnerische Qualität verwenden exakt dasselbe Evidenzmodell wie der Generator.",
      ),
      modeNavigation(basis, scope, parameter),
      coverageSummary(payload),
      this.rail.element,
    );
    this.append(payload.items, scope, basis);
    if (!this.collection.children.length)
      this.rail.append(emptyMessage("Keine Evidenz für diesen Filter."));
  }

  /** @param {unknown} values @param {string} scope @param {string} basis */
  append(values, scope = "setup", basis = "observed") {
    for (const value of Array.isArray(values) ? values : []) {
      this.rail.append(
        scope === "parameter"
          ? parameterCard(value, basis, this.images)
          : setupCard(value, basis, this.images),
      );
    }
  }

  /** Release the owned carousel. */
  dispose() {
    this.rail.dispose();
  }
}

/** @param {string} basis @param {string} scope @param {string} parameter */
function modeNavigation(basis, scope, parameter) {
  const wrapper = document.createElement("div");
  wrapper.className = "analytics-guidance-navigation";
  const bases = document.createElement("nav");
  bases.className = "analytics-subtabs";
  bases.setAttribute("aria-label", "Evidenzgrundlage");
  for (const [value, label] of [
    ["observed", "Gesichtet"],
    ["predicted", "Rechnerisch"],
  ]) {
    const button = modeButton(label, value === basis);
    button.dataset.guidanceBasis = value;
    bases.append(button);
  }
  const scopes = document.createElement("nav");
  scopes.className = "analytics-subtabs";
  scopes.setAttribute("aria-label", "Evidenzebene");
  for (const [value, label] of [
    ["setup", "Gesamtsetup"],
    ["parameter", "Einzelwerte"],
  ]) {
    const button = modeButton(label, value === scope);
    button.dataset.guidanceScope = value;
    scopes.append(button);
  }
  wrapper.append(bases, scopes);
  if (scope === "parameter") {
    const parameters = document.createElement("nav");
    parameters.className = "analytics-subtabs analytics-parameter-tabs";
    parameters.setAttribute("aria-label", "Renderparameter");
    for (const [value, label] of parameterLabels) {
      if (["aspect_format", "resolution_class"].includes(value)) continue;
      const button = modeButton(label, value === parameter);
      button.dataset.guidanceScope = "parameter";
      button.dataset.guidanceParameter = value;
      parameters.append(button);
    }
    wrapper.append(parameters);
  }
  return wrapper;
}

/** @param {Record<string, any>} payload */
function coverageSummary(payload) {
  const coverage = recordValue(payload.coverage);
  const element = document.createElement("p");
  element.className = "analytics-coverage-summary";
  element.textContent = `${textValue(coverage.observed_setup_count)} Setups beobachtet · ${textValue(coverage.stable_setup_count)} ab fünf unabhängigen Bildern ausreichend gesichtet · ${textValue(payload.filtered_total)} im aktuellen Filter`;
  return element;
}

/** @param {Record<string, any>} item @param {string} basis @param {import("./evidence-image-strip.js").EvidenceImageStrip} images */
function setupCard(item, basis, images) {
  const row = recordValue(item);
  const settings = recordValue(row.settings);
  const evidence = recordValue(row.evidence);
  const card = cardShell(evidence, basis);
  const heading = document.createElement("strong");
  heading.textContent = String(settings.checkpoint || "Unbekanntes Setup");
  const values = document.createElement("span");
  values.textContent = `Sampler ${textValue(settings.sampler)} · ${textValue(settings.scheduler)} · Steps ${textValue(settings.steps)} · CFG ${textValue(settings.cfg)} · Denoise ${textValue(settings.denoise)}`;
  const support = evidenceLine(evidence, basis);
  const intentKind = basis === "predicted" ? "recommendation" : "render_setup";
  const action = createGeneratorHandoffAction(intentKind, {
    className: "analytics-use-button",
    data:
      basis === "predicted"
        ? { recommendation: JSON.stringify(settings) }
        : { renderSetup: JSON.stringify(settings) },
    disabled: row.applicable === false,
  });
  const body = cardBody(
    heading,
    values,
    support,
    analyticsActionGroup(createBestImagePromptAction(row.best_images), action),
  );
  card.append(images.render(row.best_images, "Render-Setup"), body);
  return card;
}

/** @param {Record<string, any>} item @param {string} basis @param {import("./evidence-image-strip.js").EvidenceImageStrip} images */
function parameterCard(item, basis, images) {
  const row = recordValue(item);
  const evidence = recordValue(row[basis]);
  const card = cardShell(evidence, basis);
  const heading = document.createElement("strong");
  heading.textContent = `${parameterLabels.get(String(row.parameter)) || textValue(row.parameter)}: ${textValue(row.value)}`;
  const support = evidenceLine(evidence, basis);
  const action = createGeneratorHandoffAction("parameter", {
    className: "analytics-use-button",
    data: {
      parameter: String(row.parameter || ""),
      value: String(row.value || ""),
    },
    disabled: row.applicable === false,
  });
  const body = cardBody(
    heading,
    support,
    analyticsActionGroup(createBestImagePromptAction(row.best_images), action),
  );
  card.append(images.render(row.best_images, heading.textContent), body);
  return card;
}

/** @param {...HTMLElement} elements */
function cardBody(...elements) {
  const body = document.createElement("div");
  body.className = "analytics-card-body";
  body.append(...elements);
  return body;
}

/** @param {Record<string, any>} evidence @param {string} basis */
function cardShell(evidence, basis) {
  const card = document.createElement("article");
  card.className = "analytics-guidance-card media-card";
  card.dataset.source = basis;
  const rank =
    evidence.relative_rank == null
      ? Number.NaN
      : Number(evidence.relative_rank);
  card.dataset.tone = Number.isFinite(rank)
    ? rank >= 0.67
      ? "high"
      : rank >= 0.34
        ? "medium"
        : "low"
    : "neutral";
  return card;
}

/** @param {Record<string, any>} evidence @param {string} basis */
function evidenceLine(evidence, basis) {
  const line = document.createElement("span");
  const score = Number(evidence.expected_success_rate) * 100;
  line.textContent = `${Number.isFinite(score) ? score.toFixed(1) : "–"} % ${basis === "predicted" ? "prognostizierter" : "beobachteter"} Erfolg · ${textValue(evidence.image_count)} unabhängige Bilder · ${textValue(evidence.review_count)} Reviews · ${confidenceLabel(String(evidence.confidence || ""))}`;
  return line;
}

/** @param {string} label @param {boolean} pressed */
function modeButton(label, pressed) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.setAttribute("aria-pressed", String(pressed));
  return button;
}

/** @param {string} value */
function confidenceLabel(value) {
  return (
    {
      insufficient: "nicht belastbar",
      low: "geringe Evidenz",
      medium: "mittlere Sicherheit",
      high: "hohe Sicherheit",
    }[value] || "unbekannt"
  );
}
