/** Own the bounded visual evidence strip for one catalog component. */
export class CatalogEvidenceView {
  /** @param {{onOpen: (imageUid: string, imageUrl: string) => void}} actions */
  constructor(actions) {
    this.actions = actions;
    this.element = document.createElement("section");
    this.element.className = "catalog-evidence";
    this.abortController = new AbortController();
  }

  /** @param {Array<Record<string, any>>} images */
  render(images) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.element.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "catalog-evidence-heading";
    const title = document.createElement("h3");
    title.textContent = "Top-Beispielbilder";
    const note = document.createElement("span");
    note.textContent = "Kanonisch zugeordnet · nach Bewertung";
    heading.append(title, note);
    this.element.append(heading);

    const visible = images.filter((image) => image.image_url).slice(0, 3);
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "catalog-evidence-empty";
      empty.textContent = "Noch keine bewerteten Beispielbilder vorhanden.";
      this.element.append(empty);
      return;
    }

    const strip = document.createElement("div");
    strip.className = "catalog-evidence-strip";
    strip.dataset.imageCount = String(visible.length);
    for (const image of visible) {
      strip.append(this.#imageButton(image));
    }
    this.element.append(strip);
  }

  /** Release image interaction listeners. */
  dispose() {
    this.abortController.abort();
    this.element.replaceChildren();
  }

  /** @param {Record<string, any>} evidence */
  #imageButton(evidence) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "catalog-evidence-image";
    button.setAttribute("aria-label", "Beispielbild vergrößern");
    const image = document.createElement("img");
    image.src = String(evidence.image_url);
    image.alt = "Kanonisches Beispielbild";
    image.loading = "lazy";
    image.decoding = "async";
    const rating = document.createElement("span");
    const average = Number(evidence.average_rating);
    rating.textContent = Number.isFinite(average)
      ? `Ø ${average.toLocaleString("de-DE", { maximumFractionDigits: 1 })} / 10`
      : "Noch unbewertet";
    button.append(image, rating);
    button.addEventListener(
      "click",
      () =>
        this.actions.onOpen(
          String(evidence.image_uid || ""),
          String(evidence.image_url || ""),
        ),
      { signal: this.abortController.signal },
    );
    return button;
  }
}
