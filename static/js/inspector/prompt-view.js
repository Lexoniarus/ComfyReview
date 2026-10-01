/** Render the immutable positive and negative generation snapshots. */
export class PromptView {
  constructor() {
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-prompts";
  }

  /** @param {Record<string, any>} image */
  render(image) {
    const snapshot = image.prompt_snapshot || {};
    const heading = document.createElement("h3");
    heading.textContent = snapshot.draft_overridden
      ? "Prompt · Draft-Override"
      : "Prompt";
    this.element.replaceChildren(
      heading,
      promptBlock("Positiv", snapshot.positive),
      promptBlock("Negativ", snapshot.negative),
    );
  }
}

/** @param {string} label @param {unknown} value */
function promptBlock(label, value) {
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = label;
  const text = document.createElement("p");
  text.className = label === "Negativ" ? "muted" : "";
  text.textContent = String(value || "—");
  details.append(summary, text);
  return details;
}
