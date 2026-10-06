/** Own cyclic pointer, wheel and button navigation for one card rail. */
export class CyclicCardRail {
  /**
   * @param {HTMLElement} root
   * @param {{trackSelector?: string, itemSelector?: string}} [options]
   */
  constructor(root, options = {}) {
    this.root = root;
    this.trackSelector = options.trackSelector || "[data-card-rail-track]";
    this.itemSelector = options.itemSelector || "[data-card-rail-item]";
    this.track = /** @type {HTMLElement} */ (
      root.querySelector(this.trackSelector)
    );
    this.abortController = new AbortController();
    this.currentIndex = 0;
    this.touchStartX = null;
    this.touchStartY = null;
    this.horizontalGesture = false;
    this.root.addEventListener("click", (event) => this.#onClick(event), {
      signal: this.abortController.signal,
    });
    this.track.addEventListener("wheel", (event) => this.#onWheel(event), {
      signal: this.abortController.signal,
      passive: false,
    });
    this.track.addEventListener(
      "touchstart",
      (event) => this.#onTouchStart(event),
      { signal: this.abortController.signal, passive: true },
    );
    this.track.addEventListener(
      "touchmove",
      (event) => this.#onTouchMove(event),
      { signal: this.abortController.signal, passive: false },
    );
    this.track.addEventListener(
      "touchend",
      (event) => this.#onTouchEnd(event),
      {
        signal: this.abortController.signal,
        passive: true,
      },
    );
    this.refresh();
  }

  /** Re-evaluate cards after incremental rendering. */
  refresh() {
    const cards = this.#cards();
    if (cards.length && this.currentIndex >= cards.length)
      this.currentIndex = 0;
    this.track.dataset.cardRailIndex = String(this.currentIndex);
    this.track.dataset.carouselIndex = String(this.currentIndex);
    for (const button of this.root.querySelectorAll(
      "[data-card-rail-direction], [data-carousel-direction]",
    )) {
      if (button instanceof HTMLButtonElement) button.hidden = cards.length < 2;
    }
  }

  /** @param {-1 | 1} direction */
  move(direction) {
    const cards = this.#cards();
    if (cards.length < 2) return;
    this.currentIndex =
      (this.currentIndex + direction + cards.length) % cards.length;
    this.track.dataset.cardRailIndex = String(this.currentIndex);
    this.track.dataset.carouselIndex = String(this.currentIndex);
    const target = /** @type {HTMLElement} */ (cards[this.currentIndex]);
    const left = Math.max(target.offsetLeft - this.track.offsetLeft, 0);
    if (typeof this.track.scrollTo === "function") {
      this.track.scrollTo({ left, behavior: "smooth" });
    } else {
      this.track.scrollLeft = left;
    }
  }

  /** Release every listener owned by this rail. */
  dispose() {
    this.abortController.abort();
  }

  /** @param {Event} event */
  #onClick(event) {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest(
      "[data-card-rail-direction], [data-carousel-direction]",
    );
    if (!(button instanceof HTMLElement)) return;
    const direction =
      button.dataset.cardRailDirection || button.dataset.carouselDirection;
    this.move(direction === "previous" ? -1 : 1);
  }

  /** @param {WheelEvent} event */
  #onWheel(event) {
    if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return;
    event.preventDefault();
    this.move(event.deltaX < 0 ? -1 : 1);
  }

  /** @param {TouchEvent} event */
  #onTouchStart(event) {
    this.touchStartX = event.touches[0]?.clientX ?? null;
    this.touchStartY = event.touches[0]?.clientY ?? null;
    this.horizontalGesture = false;
  }

  /** @param {TouchEvent} event */
  #onTouchMove(event) {
    if (this.touchStartX === null || this.touchStartY === null) return;
    const touch = event.touches[0];
    if (!touch) return;
    const deltaX = Math.abs(this.touchStartX - touch.clientX);
    const deltaY = Math.abs(this.touchStartY - touch.clientY);
    if (deltaX > deltaY && deltaX >= 8) {
      this.horizontalGesture = true;
      event.preventDefault();
    }
  }

  /** @param {TouchEvent} event */
  #onTouchEnd(event) {
    if (this.touchStartX === null) return;
    const endX = event.changedTouches[0]?.clientX ?? this.touchStartX;
    const delta = this.touchStartX - endX;
    this.touchStartX = null;
    this.touchStartY = null;
    if (this.horizontalGesture && Math.abs(delta) >= 24) {
      this.move(delta < 0 ? -1 : 1);
    }
    this.horizontalGesture = false;
  }

  #cards() {
    return Array.from(this.track.querySelectorAll(this.itemSelector));
  }
}
