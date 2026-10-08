const numberFormatter = new Intl.NumberFormat("de-DE", {
  maximumFractionDigits: 2,
});

export const parameterLabels = new Map([
  ["checkpoint", "Checkpoint"],
  ["steps", "Steps"],
  ["cfg", "CFG"],
  ["sampler", "Sampler"],
  ["scheduler", "Scheduler"],
  ["denoise", "Denoise"],
  ["aspect_format", "Format / Ausrichtung"],
  ["resolution_class", "Auflösungsklasse"],
]);

export const scopeKindLabels = new Map([
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
]);

/** @param {unknown} value */
export function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

/** @param {unknown} value @returns {Record<string, any>} */
export function recordValue(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

/** @param {unknown} value */
export function textValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

/** @param {unknown} value */
export function decimalValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? numberFormatter.format(number) : "—";
}

/** @param {unknown} value */
export function percentValue(value) {
  const number = Number(value);
  return Number.isFinite(number)
    ? `${numberFormatter.format(number * 100)} %`
    : "—";
}

/** @param {Record<string, any>} item */
export function settingLine(item) {
  return `${textValue(item.sampler)} · ${textValue(item.scheduler)} · ${textValue(item.steps)} Steps · CFG ${textValue(item.cfg)}`;
}

/** @param {Record<string, any>} stage */
export function stageLine(stage) {
  return `${textValue(stage.role)} · ${textValue(stage.sampler)} / ${textValue(stage.scheduler)} · ${textValue(stage.steps)} Steps · CFG ${textValue(stage.cfg)} · Denoise ${textValue(stage.denoise)}`;
}

/** @param {string} text */
export function sectionTitle(text) {
  const title = document.createElement("h2");
  title.textContent = text;
  return title;
}

/** @param {string} text */
export function emptyMessage(text) {
  const message = document.createElement("p");
  message.className = "analytics-empty";
  message.textContent = text;
  return message;
}

/** @param {string} title @param {string} description */
export function reportIntro(title, description) {
  const header = document.createElement("header");
  header.className = "analytics-report-intro";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const copy = document.createElement("p");
  copy.textContent = description;
  header.append(heading, copy);
  return header;
}
