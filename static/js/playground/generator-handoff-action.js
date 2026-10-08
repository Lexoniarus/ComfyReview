const labels = Object.freeze({
  prompt: "Prompt & LoRAs übernehmen",
  best_image_prompt: "Prompt & LoRAs des Bestbilds übernehmen",
  scope: "Prompt & LoRAs übernehmen",
  composition: "Prompt & LoRAs übernehmen",
  combination: "Prompt & LoRAs übernehmen",
  render: "Generierungseinstellungen übernehmen",
  render_setup: "Generierungseinstellungen übernehmen",
  recommendation: "Generierungseinstellungen übernehmen",
  parameter: "Parameter übernehmen",
});

/**
 * Create the shared direct-to-Generator action used by every source surface.
 * @param {keyof typeof labels} kind
 * @param {{variant?: "compact" | "prominent", data?: Record<string, string>, disabled?: boolean, className?: string}} [options]
 */
export function createGeneratorHandoffAction(kind, options = {}) {
  const variant = options.variant || "prominent";
  const button = document.createElement("button");
  button.type = "button";
  button.className = [
    variant === "prominent" ? "secondary-button" : "ghost-button",
    "generator-handoff-action",
    `generator-handoff-action-${variant}`,
    options.className || "",
  ]
    .filter(Boolean)
    .join(" ");
  button.dataset.playgroundIntent = kind;
  for (const [name, value] of Object.entries(options.data || {})) {
    button.dataset[name] = value;
  }
  button.disabled = Boolean(options.disabled);
  button.textContent = labels[kind];
  return button;
}
