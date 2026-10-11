/** Render the current pool and ordered POC deck from server projections. */
export class CardDeckView {
  /** @param {HTMLElement} root @param {{onAdd: (cardId: string) => void, onRemove: (cardId: string) => void, onMove: (cardId: string, direction: number) => void, onDevelop: (cardId: string) => void}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.status = requiredElement(root, "[data-deck-status]");
    this.capacity = requiredElement(root, "[data-deck-capacity]");
    this.deckList = requiredElement(root, "[data-deck-list]");
    this.poolList = requiredElement(root, "[data-card-pool]");
  }

  /** @param {{deck: Record<string, any>, pool: Array<Record<string, any>>}} payload */
  render(payload) {
    const entries = Array.isArray(payload.deck?.entries)
      ? payload.deck.entries
      : [];
    const pool = Array.isArray(payload.pool) ? payload.pool : [];
    const deckIds = new Set(entries.map((entry) => String(entry.card_id)));
    this.capacity.textContent = `${entries.length} / ${Number(payload.deck?.capacity || 40)}`;
    this.status.textContent = `Deck Revision ${Number(payload.deck?.revision || 0)}`;
    this.deckList.replaceChildren(
      ...(entries.length
        ? entries.map((entry, index) =>
            this.#deckCard(entry, index, entries.length),
          )
        : [message("card-empty-state", "Das POC-Deck ist noch leer.")]),
    );
    this.poolList.replaceChildren(
      ...(pool.length
        ? pool.map((card) => this.#poolCard(card, deckIds.has(card.card_id)))
        : [message("card-empty-state", "Noch keine Karten im Pool.")]),
    );
  }

  /** @param {boolean} busy */
  setBusy(busy) {
    for (const button of this.root.querySelectorAll("button")) {
      button.disabled = busy || button.dataset.allowed === "false";
    }
  }

  /** @param {string} text */
  showError(text) {
    this.status.textContent = text;
  }

  dispose() {
    this.deckList.replaceChildren();
    this.poolList.replaceChildren();
  }

  /** @param {Record<string, any>} entry @param {number} index @param {number} length */
  #deckCard(entry, index, length) {
    const article = cardArticle(entry.card, `Deckplatz ${index + 1}`);
    const controls = document.createElement("footer");
    controls.className = "deck-card-controls";
    controls.append(
      actionButton("↑", index > 0, () =>
        this.actions.onMove(entry.card_id, -1),
      ),
      actionButton("↓", index < length - 1, () =>
        this.actions.onMove(entry.card_id, 1),
      ),
      actionButton("Entfernen", true, () =>
        this.actions.onRemove(entry.card_id),
      ),
      actionButton(
        "Entwickeln",
        Boolean(entry.card?.actions?.can_develop),
        () => this.actions.onDevelop(entry.card_id),
      ),
    );
    article.append(controls);
    return article;
  }

  /** @param {Record<string, any>} card @param {boolean} inDeck */
  #poolCard(card, inDeck) {
    const article = cardArticle(card, inDeck ? "Im Deck" : "Kartenpool");
    const controls = document.createElement("footer");
    controls.className = "deck-card-controls";
    controls.append(
      actionButton(inDeck ? "Bereits im Deck" : "Zum Deck", !inDeck, () =>
        this.actions.onAdd(card.card_id),
      ),
      actionButton("Entwickeln", Boolean(card.actions?.can_develop), () =>
        this.actions.onDevelop(card.card_id),
      ),
    );
    article.append(controls);
    return article;
  }
}

/** @param {Record<string, any>|null|undefined} card @param {string} label */
function cardArticle(card, label) {
  const article = document.createElement("article");
  article.className = "pool-card";
  if (!card) {
    article.append(message("card-error-state", "Karte nicht verfügbar"));
    return article;
  }
  const image = document.createElement("img");
  image.src = String(card.active_image?.image_url || "");
  image.alt = "Aktuelles Kartenbild";
  image.loading = "lazy";
  const body = document.createElement("div");
  body.className = "pool-card-body";
  const eyebrow = document.createElement("span");
  eyebrow.className = "pool-card-eyebrow";
  eyebrow.textContent = `${label} · ${String(card.card_spec?.rarity_key || "card").toUpperCase()} L${Number(card.card_spec?.level || 0)}`;
  const title = document.createElement("h3");
  title.textContent = String(
    card.presentation?.presentation?.card_title || card.card_id,
  );
  const stats = document.createElement("p");
  stats.textContent = `ATK ${card.card_spec?.stats?.attack ?? "–"} · DEF ${card.card_spec?.stats?.defense ?? "–"}`;
  body.append(eyebrow, title, stats);
  article.append(image, body);
  return article;
}

/** @param {string} label @param {boolean} allowed @param {() => void} action */
function actionButton(label, allowed, action) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary-button";
  button.textContent = label;
  button.dataset.allowed = allowed ? "true" : "false";
  button.disabled = !allowed;
  button.addEventListener("click", action);
  return button;
}

/** @param {string} className @param {string} text */
function message(className, text) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  paragraph.textContent = text;
  return paragraph;
}

/** @param {ParentNode} root @param {string} selector */
function requiredElement(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLElement)) throw new Error(`Missing ${selector}`);
  return element;
}
