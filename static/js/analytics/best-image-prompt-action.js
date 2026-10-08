import { arrayValue, recordValue } from "./analytics-formatters.js";
import { createGeneratorHandoffAction } from "../playground/generator-handoff-action.js";

/**
 * Create one explicit prompt/LoRA handoff from the server-ranked best image.
 * @param {unknown} bestImages
 */
export function createBestImagePromptAction(bestImages) {
  const bestImage = recordValue(arrayValue(bestImages)[0]);
  const imageUid = String(bestImage.image_uid || "").trim();
  return createGeneratorHandoffAction("best_image_prompt", {
    className: "analytics-use-button",
    data: { imageUid },
    disabled: !imageUid,
  });
}

/**
 * Group independent Analytics handoff actions without merging their intent.
 * @param {...HTMLElement} actions
 */
export function analyticsActionGroup(...actions) {
  const group = document.createElement("div");
  group.className = "analytics-use-actions";
  group.append(...actions);
  return group;
}
