import { EvidenceCarousel } from "../components/evidence-carousel.js";
import { CyclicCardRail } from "../components/cyclic-card-rail.js";

/** Render the two canonical Playground evidence groups. */
export class TopCombinationsView {
  /** @param {HTMLElement} root @param {{open: (element: HTMLElement) => void}} navigator @param {{createGeneratorActions?: (imageUid: string) => HTMLElement}} [options] */
  constructor(root, navigator, options = {}) {
    this.root = root;
    this.navigator = navigator;
    this.createGeneratorActions = options.createGeneratorActions;
    this.abortController = new AbortController();
    /** @type {CyclicCardRail[]} */
    this.carousels = [];
    /** @type {EvidenceCarousel[]} */
    this.evidenceCarousels = [];
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
    const groups = characterGroups(payload);
    const twoComponent = combinationCollection(
      "Top 2er-Kombinationen",
      "Charakter + Szene · getrennt nach Charakter",
      groups,
      "two_component",
      this.evidenceCarousels,
      this.createGeneratorActions,
    );
    const threeComponent = combinationCollection(
      "Top 3er-Kombinationen",
      "Charakter + Szene + Outfit · getrennt nach Charakter",
      groups,
      "three_component",
      this.evidenceCarousels,
      this.createGeneratorActions,
    );
    this.root.replaceChildren(twoComponent, threeComponent);
    this.carousels = Array.from(
      this.root.querySelectorAll("[data-card-rail]"),
      (element) =>
        new CyclicCardRail(/** @type {HTMLElement} */ (element), {
          itemSelector: ".playground-combination-card",
        }),
    );
  }

  /** Remove rendered evidence. */
  dispose() {
    this.#disposeCarousels();
    this.abortController.abort();
    this.root.replaceChildren();
  }

  #disposeCarousels() {
    for (const carousel of this.carousels) carousel.dispose();
    for (const carousel of this.evidenceCarousels) carousel.dispose();
    this.carousels = [];
    this.evidenceCarousels = [];
  }
}

/** @param {string} title @param {string} subtitle @param {Record<string, any>[]} groups @param {"two_component" | "three_component"} field @param {EvidenceCarousel[]} evidenceCarousels @param {((imageUid: string) => HTMLElement) | undefined} createGeneratorActions */
function combinationCollection(
  title,
  subtitle,
  groups,
  field,
  evidenceCarousels,
  createGeneratorActions,
) {
  const section = document.createElement("section");
  section.className = "playground-combination-group";
  const heading = document.createElement("header");
  const titleElement = document.createElement("h2");
  titleElement.textContent = title;
  const description = document.createElement("p");
  description.textContent = subtitle;
  heading.append(titleElement, description);
  section.append(heading);
  let populated = false;
  for (const group of groups) {
    const rows = arrayValue(group[field]);
    if (!rows.length) continue;
    populated = true;
    section.append(
      characterCombinationRow(
        group,
        rows,
        evidenceCarousels,
        createGeneratorActions,
      ),
    );
  }
  if (!populated) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Noch keine ausreichend belegten Kombinationen.";
    section.append(empty);
  }
  return section;
}

/** @param {Record<string, any>} group @param {unknown[]} rows @param {EvidenceCarousel[]} evidenceCarousels @param {((imageUid: string) => HTMLElement) | undefined} createGeneratorActions */
function characterCombinationRow(
  group,
  rows,
  evidenceCarousels,
  createGeneratorActions,
) {
  const row = document.createElement("section");
  row.className = "playground-character-row";
  const title = document.createElement("h3");
  title.textContent = String(group.character_name || "Unbekannter Charakter");
  const carousel = document.createElement("div");
  carousel.className = "playground-carousel";
  carousel.dataset.cardRail = "";
  const grid = document.createElement("div");
  grid.className = "playground-combination-grid";
  grid.dataset.cardRailTrack = "";
  grid.dataset.carouselTrack = "";
  grid.dataset.carouselIndex = "0";
  for (const value of rows) {
    grid.append(
      combinationCard(
        recordValue(value),
        evidenceCarousels,
        createGeneratorActions,
      ),
    );
  }
  carousel.append(
    carouselButton("previous", "Vorherige Kombinationen", "‹"),
    grid,
    carouselButton("next", "Nächste Kombinationen", "›"),
  );
  row.append(title, carousel);
  return row;
}

/** @param {"previous" | "next"} direction @param {string} label @param {string} glyph */
function carouselButton(direction, label, glyph) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `playground-carousel-button is-${direction}`;
  button.dataset.cardRailDirection = direction;
  button.dataset.carouselDirection = direction;
  button.setAttribute("aria-label", label);
  button.textContent = glyph;
  return button;
}

/** @param {Record<string, any>} row @param {EvidenceCarousel[]} evidenceCarousels @param {((imageUid: string) => HTMLElement) | undefined} createGeneratorActions */
function combinationCard(row, evidenceCarousels, createGeneratorActions) {
  const card = document.createElement("article");
  card.className = "playground-combination-card media-card";
  card.dataset.cardRailItem = "";
  const carousel = new EvidenceCarousel({
    className: "playground-combination-images media-card-image",
    isolateGestures: true,
    createGeneratorActions,
  });
  evidenceCarousels.push(carousel);
  const evidenceImages = arrayValue(row.best_images)
    .slice(0, 3)
    .map(recordValue);
  card.dataset.imageCount = String(
    evidenceImages.filter((item) => item.image_url || item.url).length,
  );
  const images = carousel.render(
    evidenceImages,
    `${String(row.label || "Kombination")} · Beispiel`,
  );
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

/** @param {Record<string, any>} payload */
function characterGroups(payload) {
  const groups = arrayValue(payload.characters).map(recordValue);
  if (groups.length) return groups;
  return [
    {
      character_uid: "all",
      character_name: "Alle Charaktere",
      two_component: arrayValue(payload.two_component),
      three_component: arrayValue(payload.three_component),
    },
  ];
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
