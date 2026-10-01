const DRAWER_QUERY = "(max-width: 85.375rem), (pointer: coarse)";
const COMPACT_QUERY =
  "(min-width: 85.4375rem) and (max-width: 112.4999rem) and (pointer: fine)";

/** @typedef {{drawer: MediaQueryList, compact: MediaQueryList}} RailMediaQueries */

/** Own responsive rail visibility, focus, and accessibility state. */
export class ResponsiveRails {
  /** @param {HTMLElement} root @param {RailMediaQueries} [queries] */
  constructor(root, queries = createMediaQueries()) {
    this.root = root;
    this.queries = queries;
    this.events = new AbortController();
    this.handleMediaChange = () => this.#resetLayout();
    this.root.addEventListener("click", (event) => this.#handleClick(event), {
      signal: this.events.signal,
    });
    this.root.addEventListener("keydown", (event) => this.#handleKey(event), {
      signal: this.events.signal,
    });
    this.queries.drawer.addEventListener("change", this.handleMediaChange);
    this.queries.compact.addEventListener("change", this.handleMediaChange);
    this.#reflectAll();
  }

  /** @param {"scope" | "inspector"} rail */
  toggle(rail) {
    this.#setExpanded(rail, !this.#isExpanded(rail));
  }

  /** @param {"scope" | "inspector"} rail */
  open(rail) {
    this.#setExpanded(rail, true);
  }

  /** Release delegated controls and media-query listeners. */
  dispose() {
    this.events.abort();
    this.queries.drawer.removeEventListener("change", this.handleMediaChange);
    this.queries.compact.removeEventListener("change", this.handleMediaChange);
  }

  /** @param {Event} event */
  #handleClick(event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const button = target.closest("[data-rail-action]");
    if (!(button instanceof HTMLElement)) return;
    const rail = button.dataset.railAction;
    if (rail === "scope" || rail === "inspector") this.toggle(rail);
  }

  /** @param {KeyboardEvent} event */
  #handleKey(event) {
    if (event.key !== "Escape" || this.#mode() !== "drawer") return;
    const openRail = this.#isExpanded("scope")
      ? "scope"
      : this.#isExpanded("inspector")
        ? "inspector"
        : null;
    if (!openRail) return;
    this.#setExpanded(openRail, false);
    this.#button(openRail)?.focus();
  }

  /** @param {"scope" | "inspector"} rail @param {boolean} expanded */
  #setExpanded(rail, expanded) {
    const mode = this.#mode();
    if (mode === "wide") {
      this.#resetLayout();
      return;
    }
    if (mode === "compact") {
      this.root.classList.toggle(`${railClass(rail)}-collapsed`, !expanded);
    } else {
      this.root.classList.toggle(`${railClass(rail)}-open`, expanded);
      if (expanded) {
        const other = rail === "scope" ? "inspector" : "scope";
        this.root.classList.remove(`${railClass(other)}-open`);
      }
    }
    this.#reflectAll();
    if (expanded) this.#panel(rail)?.focus();
  }

  /** @param {"scope" | "inspector"} rail */
  #isExpanded(rail) {
    const mode = this.#mode();
    if (mode === "wide") return true;
    const state = railClass(rail);
    return mode === "compact"
      ? !this.root.classList.contains(`${state}-collapsed`)
      : this.root.classList.contains(`${state}-open`);
  }

  #resetLayout() {
    this.root.classList.remove(
      "is-scope-open",
      "is-inspector-open",
      "is-scope-collapsed",
      "is-inspector-collapsed",
    );
    this.#reflectAll();
  }

  #reflectAll() {
    this.#reflect("scope");
    this.#reflect("inspector");
  }

  /** @param {"scope" | "inspector"} rail */
  #reflect(rail) {
    const expanded = this.#isExpanded(rail);
    this.#button(rail)?.setAttribute("aria-expanded", String(expanded));
    const panel = this.#panel(rail);
    if (!panel) return;
    panel.inert = !expanded;
    if (expanded) {
      panel.removeAttribute("aria-hidden");
    } else {
      panel.setAttribute("aria-hidden", "true");
    }
  }

  #mode() {
    if (this.queries.drawer.matches) return "drawer";
    if (this.queries.compact.matches) return "compact";
    return "wide";
  }

  /** @param {"scope" | "inspector"} rail */
  #button(rail) {
    const button = this.root.querySelector(`[data-rail-action='${rail}']`);
    return button instanceof HTMLElement ? button : null;
  }

  /** @param {"scope" | "inspector"} rail */
  #panel(rail) {
    const selector =
      rail === "scope" ? "[data-scope-navigator]" : "[data-image-inspector]";
    const panel = this.root.querySelector(selector);
    if (!(panel instanceof HTMLElement)) return null;
    panel.tabIndex = -1;
    return panel;
  }
}

function createMediaQueries() {
  return {
    drawer: window.matchMedia(DRAWER_QUERY),
    compact: window.matchMedia(COMPACT_QUERY),
  };
}

/** @param {"scope" | "inspector"} rail */
function railClass(rail) {
  return rail === "scope" ? "is-scope" : "is-inspector";
}
