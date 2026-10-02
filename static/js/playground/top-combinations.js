/** Render the two canonical Playground evidence groups. */
export class TopCombinationsView {
  /** @param {HTMLElement} root @param {{open: (element: HTMLElement) => void}} navigator */
  constructor(root, navigator) {
    this.root = root;
    this.navigator = navigator;
    this.abortController = new AbortController();
    /** @type {LoopingCarousel[]} */
    this.carousels = [];
    this.root.addEventListener(
      "click",
      (event) => {
        if (!(event.target instanceof Element)) return;
        const action = event.target.closest("[data-playground-intent]");
        if (action instanceof HTMLElement) this.navigator.open(action);
      },
      { signal: this.abortController.signal },
    );
  }

  /** @param {Record<string, any>} payload */
  render(payload) {
    this.#disposeCarousels();
    const twoComponent = combinationGroup(
      "Top 2er-Kombinationen",
      "Charakter + Szene",
      arrayValue(payload.two_component),
    );
    const threeComponent = combinationGroup(
      "Top 3er-Kombinationen",
      "Charakter + Szene + Outfit",
      arrayValue(payload.three_component),
    );
    this.root.replaceChildren(twoComponent, threeComponent);
    this.carousels = [
      new LoopingCarousel(twoComponent),
      new LoopingCarousel(threeComponent),
    ];
  }

  /** Remove rendered evidence. */
  dispose() {
    this.#disposeCarousels();
    this.abortController.abort();
    this.root.replaceChildren();
  }

  #disposeCarousels() {
    for (const carousel of this.carousels) carousel.dispose();
    this.carousels = [];
  }
}

/** Own cyclic navigation and listeners for one evidence carousel. */
class LoopingCarousel {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
    this.track = /** @type {HTMLElement} */ (
      root.querySelector("[data-carousel-track]")
    );
    this.abortController = new AbortController();
    this.currentIndex = 0;
    this.root.addEventListener(
      "click",
      (event) => {
        if (!(event.target instanceof Element)) return;
        const button = event.target.closest("[data-carousel-direction]");
        if (!(button instanceof HTMLElement)) return;
        this.move(button.dataset.carouselDirection === "previous" ? -1 : 1);
      },
      { signal: this.abortController.signal },
    );
    this.#updateControls();
  }

  /** @param {-1 | 1} direction */
  move(direction) {
    const cards = Array.from(
      this.track.querySelectorAll(".playground-combination-card"),
    );
    if (cards.length < 2) return;
    this.currentIndex =
      (this.currentIndex + direction + cards.length) % cards.length;
    this.track.dataset.carouselIndex = String(this.currentIndex);
    const target = /** @type {HTMLElement} */ (cards[this.currentIndex]);
    if (typeof this.track.scrollTo === "function") {
      this.track.scrollTo({ left: target.offsetLeft, behavior: "smooth" });
    } else {
      this.track.scrollLeft = target.offsetLeft;
    }
  }

  /** Release every listener owned by this carousel. */
  dispose() {
    this.abortController.abort();
  }

  #updateControls() {
    const count = this.track.querySelectorAll(
      ".playground-combination-card",
    ).length;
    for (const button of this.root.querySelectorAll(
      "[data-carousel-direction]",
    )) {
      if (button instanceof HTMLButtonElement) button.hidden = count < 2;
    }
  }
}

/** @param {string} title @param {string} subtitle @param {unknown[]} rows */
function combinationGroup(title, subtitle, rows) {
  const section = document.createElement("section");
  section.className = "playground-combination-group";
  const heading = document.createElement("header");
  const titleElement = document.createElement("h2");
  titleElement.textContent = title;
  const description = document.createElement("p");
  description.textContent = subtitle;
  heading.append(titleElement, description);
  const carousel = document.createElement("div");
  carousel.className = "playground-carousel";
  const grid = document.createElement("div");
  grid.className = "playground-combination-grid";
  grid.dataset.carouselTrack = "";
  grid.dataset.carouselIndex = "0";
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Noch keine ausreichend belegten Kombinationen.";
    grid.append(empty);
  }
  for (const row of rows) grid.append(combinationCard(recordValue(row)));
  carousel.append(
    carouselButton("previous", "Vorherige Kombinationen", "‹"),
    grid,
    carouselButton("next", "Nächste Kombinationen", "›"),
  );
  section.append(heading, carousel);
  return section;
}

/** @param {"previous" | "next"} direction @param {string} label @param {string} glyph */
function carouselButton(direction, label, glyph) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `playground-carousel-button is-${direction}`;
  button.dataset.carouselDirection = direction;
  button.setAttribute("aria-label", label);
  button.textContent = glyph;
  return button;
}

/** @param {Record<string, any>} row */
function combinationCard(row) {
  const card = document.createElement("article");
  card.className = "playground-combination-card";
  const images = document.createElement("div");
  images.className = "playground-combination-images";
  for (const value of arrayValue(row.best_images).slice(0, 3)) {
    const imageValue = recordValue(value);
    if (!imageValue.url) continue;
    const image = document.createElement("img");
    image.src = String(imageValue.url);
    image.alt = `${String(row.label || "Kombination")} · Beispiel`;
    image.loading = "lazy";
    image.decoding = "async";
    images.append(image);
  }
  if (!images.children.length) {
    const missing = document.createElement("span");
    missing.textContent = "Kein Bildbeispiel";
    images.append(missing);
  }
  const imageCount = images.querySelectorAll("img").length;
  images.dataset.imageCount = String(imageCount);
  card.dataset.imageCount = String(imageCount);
  const content = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = String(row.label || "Unbenannte Kombination");
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(row.image_count)} Bilder · ${textValue(row.rating_count)} Bewertungen · Ø ${decimalValue(row.average_rating)} / 10`;
  const action = document.createElement("button");
  action.type = "button";
  action.className = "secondary-button";
  action.dataset.playgroundIntent = "scope";
  action.dataset.componentUids = JSON.stringify(arrayValue(row.component_uids));
  action.textContent = "Im Generator verwenden";
  content.append(title, evidence, action);
  card.append(images, content);
  return card;
}

/** @param {unknown} value */
function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

/** @param {unknown} value @returns {Record<string, any>} */
function recordValue(value) {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

/** @param {unknown} value */
function textValue(value) {
  return value === null || value === undefined ? "—" : String(value);
}

/** @param {unknown} value */
function decimalValue(value) {
  const number = Number(value);
  return Number.isFinite(number)
    ? new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 }).format(
        number,
      )
    : "—";
}
