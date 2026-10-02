/** Render the two canonical Playground evidence groups. */
export class TopCombinationsView {
  /** @param {HTMLElement} root */
  constructor(root) {
    this.root = root;
  }

  /** @param {Record<string, any>} payload */
  render(payload) {
    this.root.replaceChildren(
      combinationGroup(
        "Top 2er-Kombinationen",
        "Charakter + Szene",
        arrayValue(payload.two_component),
      ),
      combinationGroup(
        "Top 3er-Kombinationen",
        "Charakter + Szene + Outfit",
        arrayValue(payload.three_component),
      ),
    );
  }

  /** Remove rendered evidence. */
  dispose() {
    this.root.replaceChildren();
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
  const grid = document.createElement("div");
  grid.className = "playground-combination-grid";
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Noch keine ausreichend belegten Kombinationen.";
    grid.append(empty);
  }
  for (const row of rows) grid.append(combinationCard(recordValue(row)));
  section.append(heading, grid);
  return section;
}

/** @param {Record<string, any>} row */
function combinationCard(row) {
  const card = document.createElement("article");
  card.className = "playground-combination-card";
  const images = document.createElement("div");
  images.className = "playground-combination-images";
  for (const value of arrayValue(row.best_images)) {
    const imageValue = recordValue(value);
    if (!imageValue.url) continue;
    const image = document.createElement("img");
    image.src = String(imageValue.url);
    image.alt = `${String(row.label || "Kombination")} · Beispiel`;
    image.loading = "lazy";
    images.append(image);
  }
  if (!images.children.length) {
    const missing = document.createElement("span");
    missing.textContent = "Kein Bildbeispiel";
    images.append(missing);
  }
  const content = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = String(row.label || "Unbenannte Kombination");
  const evidence = document.createElement("span");
  evidence.textContent = `${textValue(row.image_count)} Bilder · ${textValue(row.rating_count)} Bewertungen · Ø ${decimalValue(row.average_rating)} / 10`;
  content.append(title, evidence);
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
