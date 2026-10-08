import {
  arrayValue,
  decimalValue,
  percentValue,
  recordValue,
  stageLine,
  textValue,
} from "./analytics-formatters.js";
import { createGeneratorHandoffAction } from "../playground/generator-handoff-action.js";
import {
  analyticsActionGroup,
  createBestImagePromptAction,
} from "./best-image-prompt-action.js";

/** Render one observed technical setup with bounded evidence. */
export class RenderSetupView {
  /** @param {{images: import("./evidence-image-strip.js").EvidenceImageStrip}} dependencies */
  constructor(dependencies) {
    this.images = dependencies.images;
  }

  /** @param {unknown} value */
  render(value) {
    const item = recordValue(value);
    const card = document.createElement("article");
    card.className = "analytics-render-setup";
    card.dataset.itemKey = String(item.setup_key || "");
    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = textValue(item.checkpoint);
    const action = createGeneratorHandoffAction("render_setup", {
      className: "analytics-use-button",
      data: {
        setupKey: String(item.setup_key || ""),
        renderSetup: JSON.stringify(item),
      },
    });
    header.append(
      title,
      analyticsActionGroup(
        createBestImagePromptAction(item.best_images),
        action,
      ),
    );
    const stages = document.createElement("div");
    stages.className = "analytics-stage-list";
    for (const stage of arrayValue(item.stages)) {
      const line = document.createElement("span");
      line.textContent = stageLine(recordValue(stage));
      stages.append(line);
    }
    const evidence = document.createElement("p");
    evidence.className = "analytics-evidence";
    evidence.textContent = `${textValue(item.image_count)} Bilder · ${textValue(item.rating_count)} Bewertungen · Ø ${decimalValue(item.average_rating)} / 10 · Untergrenze ${percentValue(item.lower_bound)}`;
    card.append(
      header,
      stages,
      evidence,
      this.images.render(item.best_images, "Render-Setup"),
    );
    return card;
  }
}
