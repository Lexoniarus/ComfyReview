/** Render normalized generation settings and output identity. */
export class GenerationView {
  constructor() {
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-generation";
  }

  /** @param {Record<string, any>} image */
  render(image) {
    const settings = image.generation_settings || {};
    const heading = document.createElement("h3");
    heading.textContent = "Generation";
    const facts = document.createElement("dl");
    facts.className = "inspector-compact-facts";
    appendFact(facts, "Modell", settings.model);
    appendFact(facts, "Checkpoint", settings.checkpoint);
    appendFact(facts, "Seed", settings.seed);
    appendFact(facts, "Schritte", settings.steps);
    appendFact(facts, "CFG", settings.cfg);
    appendFact(facts, "Sampler", settings.sampler);
    appendFact(facts, "Scheduler", settings.scheduler);
    appendFact(facts, "Denoise", settings.denoise);
    appendFact(facts, "Output", outputLabel(image));
    const geometry = image.geometry || {};
    appendFact(
      facts,
      "Originalmaß",
      geometry.actual_width && geometry.actual_height
        ? `${geometry.actual_width} × ${geometry.actual_height}`
        : null,
    );
    appendFact(facts, "Format", geometry.aspect_format);
    appendFact(facts, "Auflösungsklasse", geometry.resolution_class);
    appendFact(
      facts,
      "Geometriezuordnung",
      geometry.match === "exact"
        ? "Exakt"
        : geometry.match === "approximate"
          ? "Annähernd"
          : null,
    );
    this.element.replaceChildren(heading, facts);
  }
}

/** @param {Record<string, any>} image */
function outputLabel(image) {
  const role = String(image.output_role || "unbekannt");
  const index = Number.isInteger(image.output_index)
    ? Number(image.output_index)
    : "?";
  return `${role} · Index ${index}`;
}

/** @param {HTMLDListElement} root @param {string} label @param {unknown} value */
function appendFact(root, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent =
    value === null || value === undefined || value === "" ? "—" : String(value);
  root.append(term, detail);
}
