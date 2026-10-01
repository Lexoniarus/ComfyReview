import {
  normalizeScopes,
  readScopeUrlState,
  writeScopeUrlState,
} from "./url-state.js";

/** @typedef {import("./url-state.js").ScopeUrlState} ScopeUrlState */

/** Own canonical filter state and browser history synchronization. */
export class ScopeStateController {
  /** @param {Window} browserWindow */
  constructor(browserWindow) {
    this.browserWindow = browserWindow;
    this.current = readScopeUrlState(browserWindow.location.search);
    /** @type {Set<(state: ScopeUrlState) => void>} */
    this.listeners = new Set();
    this.isStarted = false;
    this.onPopState = () => {
      this.current = readScopeUrlState(this.browserWindow.location.search);
      this.#emit();
    };
  }

  /** @returns {ScopeUrlState} */
  get state() {
    return this.current;
  }

  /** Start listening for browser history navigation. */
  start() {
    if (this.isStarted) {
      return;
    }
    this.isStarted = true;
    this.browserWindow.addEventListener("popstate", this.onPopState);
    this.#emit();
  }

  /**
   * @param {(state: ScopeUrlState) => void} listener
   * @returns {() => void}
   */
  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** @param {Partial<ScopeUrlState>} patch @param {{replace?: boolean}} [options] */
  update(patch, options = {}) {
    this.current = {
      ...this.current,
      ...patch,
      scopes: normalizeScopes(patch.scopes ?? this.current.scopes),
      offset: patch.offset ?? 0,
    };
    const url = `${this.browserWindow.location.pathname}${writeScopeUrlState(this.current)}`;
    const method = options.replace ? "replaceState" : "pushState";
    this.browserWindow.history[method](null, "", url);
    this.#emit();
  }

  /** Stop listening and release subscribers. */
  dispose() {
    if (!this.isStarted) {
      return;
    }
    this.isStarted = false;
    this.browserWindow.removeEventListener("popstate", this.onPopState);
    this.listeners.clear();
  }

  #emit() {
    for (const listener of this.listeners) {
      listener(this.current);
    }
  }
}
