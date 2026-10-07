/** Own reusable cyclic image evidence with pointer, wheel and keyboard controls. */
export class EvidenceCarousel {
  /** @param {{onSelect?: (item: Record<string, any>) => void, className?: string, isolateGestures?: boolean, createGeneratorActions?: (imageUid: string) => HTMLElement}} [options] */
  constructor(options = {}) {
    this.onSelect = options.onSelect || (() => {});
    this.className = options.className || "evidence-carousel";
    this.isolateGestures = Boolean(options.isolateGestures);
    this.createGeneratorActions = options.createGeneratorActions || null;
    this.abortController = new AbortController();
  }

  /** @param {Array<Record<string, any>>} items @param {string} label */
  render(items, label) {
    const values = items.filter((item) => item.image_url || item.url);
    const root = document.createElement("div");
    root.className = `${this.className} evidence-carousel`;
    root.dataset.count = String(values.length);
    if (!values.length) {
      const empty = document.createElement("span");
      empty.textContent = "Kein Bildbeispiel";
      root.append(empty);
      return root;
    }
    let index = 0;
    const imageButton = document.createElement("button");
    imageButton.type = "button";
    imageButton.className = "evidence-carousel-image";
    const image = document.createElement("img");
    image.loading = "lazy";
    image.decoding = "async";
    imageButton.append(image);
    const previous = navigation("‹", "Vorheriges Bild", "previous");
    const next = navigation("›", "Nächstes Bild", "next");
    const position = document.createElement("span");
    position.className = "evidence-carousel-position";
    const meta = document.createElement("span");
    meta.className = "evidence-carousel-meta";
    const actionSlot = document.createElement("div");
    actionSlot.className = "evidence-carousel-generator-actions";
    const renderCurrent = () => {
      const item = values[index];
      const url = String(item.image_url || item.url || "");
      image.src = url;
      image.alt = label;
      imageButton.dataset.imageIndex = String(index);
      position.textContent = `${index + 1} / ${values.length}`;
      const hasRating =
        item.average_rating !== undefined || item.avg_rating !== undefined;
      const hasCount = item.rating_count !== undefined;
      const rating = Number(item.average_rating ?? item.avg_rating);
      const count = Number(item.rating_count || 0);
      meta.hidden = !hasRating && !hasCount;
      meta.textContent =
        hasRating && Number.isFinite(rating)
          ? `Ø ${rating.toLocaleString("de-DE", { maximumFractionDigits: 1 })} / 10 · ${count} Bewertungen`
          : hasCount
            ? `${count} Bewertungen`
            : "";
      actionSlot.replaceChildren();
      const imageUid = String(item.image_uid || "");
      if (imageUid && this.createGeneratorActions) {
        actionSlot.append(this.createGeneratorActions(imageUid));
      }
    };
    /** @param {number} amount */
    const move = (amount) => {
      index = (index + amount + values.length) % values.length;
      renderCurrent();
    };
    previous.addEventListener("click", () => move(-1), {
      signal: this.abortController.signal,
    });
    next.addEventListener("click", () => move(1), {
      signal: this.abortController.signal,
    });
    imageButton.addEventListener("click", () => this.onSelect(values[index]), {
      signal: this.abortController.signal,
    });
    image.addEventListener(
      "error",
      () => {
        imageButton.dataset.state = "failed";
        image.alt = `${label} konnte nicht geladen werden`;
      },
      { signal: this.abortController.signal },
    );
    root.addEventListener(
      "wheel",
      (event) => {
        if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return;
        if (this.isolateGestures) event.stopPropagation();
        event.preventDefault();
        move(event.deltaX > 0 ? 1 : -1);
      },
      { passive: false, signal: this.abortController.signal },
    );
    let pointerStart = 0;
    root.addEventListener(
      "pointerdown",
      (event) => {
        if (this.isolateGestures) event.stopPropagation();
        pointerStart = event.clientX;
      },
      { signal: this.abortController.signal },
    );
    root.addEventListener(
      "pointerup",
      (event) => {
        if (this.isolateGestures) event.stopPropagation();
        const distance = event.clientX - pointerStart;
        if (Math.abs(distance) > 36) move(distance < 0 ? 1 : -1);
      },
      { signal: this.abortController.signal },
    );
    if (this.isolateGestures) {
      for (const type of ["touchstart", "touchmove", "touchend"]) {
        root.addEventListener(type, (event) => event.stopPropagation(), {
          signal: this.abortController.signal,
          passive: true,
        });
      }
    }
    if (values.length > 1) root.append(previous);
    root.append(imageButton, meta, actionSlot);
    if (values.length > 1) root.append(next, position);
    renderCurrent();
    return root;
  }

  dispose() {
    this.abortController.abort();
  }
}

/** @param {string} text @param {string} label @param {string} direction */
function navigation(text, label, direction) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `evidence-carousel-control is-${direction}`;
  button.setAttribute("aria-label", label);
  button.textContent = text;
  return button;
}
