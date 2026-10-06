import { CyclicCardRail } from "../components/cyclic-card-rail.js";

/** Own markup and lifecycle for one cyclic analytics card collection. */
export class AnalyticsCardRail {
  /** @param {string} trackClass */
  constructor(trackClass) {
    this.element = document.createElement("div");
    this.element.className = "analytics-card-rail";
    this.element.dataset.cardRail = "";
    this.track = document.createElement("div");
    this.track.className = `analytics-card-track ${trackClass}`;
    this.track.dataset.cardRailTrack = "";
    this.element.append(
      railButton("previous", "Vorherige Karten", "‹"),
      this.track,
      railButton("next", "Nächste Karten", "›"),
    );
    this.carousel = new CyclicCardRail(this.element);
  }

  /** Remove cards while preserving the owned rail. */
  clear() {
    this.track.replaceChildren();
    this.carousel.currentIndex = 0;
    this.carousel.refresh();
  }

  /** @param {...Node} nodes */
  append(...nodes) {
    for (const node of nodes) {
      if (node instanceof HTMLElement) node.dataset.cardRailItem = "";
      this.track.append(node);
    }
    this.carousel.refresh();
  }

  /** Release navigation listeners. */
  dispose() {
    this.carousel.dispose();
    this.element.replaceChildren();
  }
}

/** @param {"previous" | "next"} direction @param {string} label @param {string} glyph */
function railButton(direction, label, glyph) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `analytics-card-rail-button is-${direction}`;
  button.dataset.cardRailDirection = direction;
  button.setAttribute("aria-label", label);
  button.textContent = glyph;
  return button;
}
