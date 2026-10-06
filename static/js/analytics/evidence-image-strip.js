import { EvidenceCarousel } from "../components/evidence-carousel.js";
import { arrayValue, recordValue } from "./analytics-formatters.js";

/** Adapt shared cyclic evidence to Analytics image contracts. */
export class EvidenceImageStrip {
  /** @param {{onSelect?: (imageUid: string, imageUrl: string) => void, createGeneratorActions?: (imageUid: string) => HTMLElement}} [actions] */
  constructor(actions = {}) {
    this.onSelect = actions.onSelect || (() => {});
    this.carousel = new EvidenceCarousel({
      className: "analytics-image-strip media-card-image",
      onSelect: (item) =>
        this.onSelect(String(item.image_uid || ""), String(item.url || "")),
      createGeneratorActions: actions.createGeneratorActions,
    });
  }

  /** @param {unknown} values @param {string} label */
  render(values, label) {
    return this.carousel.render(arrayValue(values).map(recordValue), label);
  }

  dispose() {
    this.carousel.dispose();
  }
}
