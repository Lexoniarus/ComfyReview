import {
  arrayValue,
  decimalValue,
  recordValue,
} from "./analytics-formatters.js";

/** Own the image lifecycle for one bounded evidence strip. */
export class EvidenceImageStrip {
  /** @param {{onSelect?: (imageUid: string) => void}} [actions] */
  constructor(actions = {}) {
    this.onSelect = actions.onSelect || (() => {});
    this.abortController = new AbortController();
  }

  /** @param {unknown} values @param {string} label */
  render(values, label) {
    const strip = document.createElement("div");
    strip.className = "analytics-image-strip";
    for (const value of arrayValue(values).slice(0, 3)) {
      const item = recordValue(value);
      if (!item.url) continue;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "analytics-image-button";
      button.disabled = !item.image_uid;
      button.setAttribute("aria-label", `${label} im Inspector öffnen`);
      const image = document.createElement("img");
      image.src = String(item.url);
      image.alt = `${label} · Ø ${decimalValue(item.avg_rating)} / 10`;
      image.loading = "lazy";
      image.decoding = "async";
      image.addEventListener(
        "error",
        () => {
          button.dataset.state = "failed";
          image.alt = `${label} konnte nicht geladen werden`;
        },
        { signal: this.abortController.signal },
      );
      if (item.image_uid) {
        button.addEventListener(
          "click",
          () => this.onSelect(String(item.image_uid)),
          { signal: this.abortController.signal },
        );
      }
      button.append(image);
      strip.append(button);
    }
    if (!strip.children.length) {
      const empty = document.createElement("span");
      empty.textContent = "Kein Bildbeispiel";
      strip.append(empty);
    }
    strip.dataset.count = String(strip.children.length);
    return strip;
  }

  /** Release image and selection listeners. */
  dispose() {
    this.abortController.abort();
  }
}
