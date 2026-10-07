import { EvidenceCarousel } from "../components/evidence-carousel.js";

/** Own cyclic visual evidence for one catalog component. */
export class CatalogEvidenceView {
  /** @param {{onOpen: (imageUid: string, imageUrl: string) => void, createGeneratorActions?: (imageUid: string) => HTMLElement}} actions */
  constructor(actions) {
    this.actions = actions;
    this.element = document.createElement("section");
    this.element.className = "catalog-evidence";
    this.carousel = new EvidenceCarousel({
      className: "catalog-evidence-strip",
      onSelect: (item) =>
        this.actions.onOpen(
          String(item.image_uid || ""),
          String(item.image_url || ""),
        ),
      createGeneratorActions: actions.createGeneratorActions,
    });
  }

  /** @param {Array<Record<string, any>>} images */
  render(images) {
    this.element.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "catalog-evidence-heading";
    const title = document.createElement("h3");
    title.textContent = "Top-Beispielbilder";
    const note = document.createElement("span");
    note.textContent = "Kanonisch zugeordnet · nach Bewertung";
    heading.append(title, note);
    this.element.append(heading);
    const visible = images.filter((image) => image.image_url);
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "catalog-evidence-empty";
      empty.textContent = "Noch keine bewerteten Beispielbilder vorhanden.";
      this.element.append(empty);
      return;
    }
    this.element.append(
      this.carousel.render(visible, "Kanonisches Beispielbild"),
    );
  }

  dispose() {
    this.carousel.dispose();
    this.element.replaceChildren();
  }
}
