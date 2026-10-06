import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResponsiveRails } from "../../static/js/layout/responsive-rails.js";

describe("ResponsiveRails", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("keeps drawers mutually exclusive and restores trigger focus", () => {
    const root = railRoot();
    const drawer = mediaQuery(true);
    const compact = mediaQuery(false);
    const rails = new ResponsiveRails(root, { drawer, compact });
    const scopeButton = button(root, "scope");
    const inspectorButton = button(root, "inspector");
    const scopePanel = panel(root, "[data-scope-navigator]");
    const inspectorPanel = panel(root, "[data-image-inspector]");

    expect(scopeButton.getAttribute("aria-expanded")).toBe("false");
    expect(scopePanel.inert).toBe(true);
    expect(scopePanel.getAttribute("aria-hidden")).toBe("true");

    scopeButton.click();
    expect(root.classList.contains("is-scope-open")).toBe(true);
    expect(document.activeElement).toBe(scopePanel);
    inspectorButton.click();
    expect(root.classList.contains("is-scope-open")).toBe(false);
    expect(root.classList.contains("is-inspector-open")).toBe(true);
    expect(scopePanel.inert).toBe(true);
    expect(inspectorPanel.inert).toBe(false);
    expect(rails.isDrawerMode()).toBe(true);
    expect(rails.isOpen("inspector")).toBe(true);

    rails.close("inspector");
    expect(root.classList.contains("is-inspector-open")).toBe(false);
    rails.open("inspector");

    root.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab" }));
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(root.classList.contains("is-inspector-open")).toBe(false);
    expect(document.activeElement).toBe(inspectorButton);
    root.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));

    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    const unknown = document.createElement("button");
    unknown.dataset.railAction = "unknown";
    root.append(unknown);
    unknown.click();

    rails.dispose();
    scopeButton.click();
    expect(root.classList.contains("is-scope-open")).toBe(false);
  });

  it("collapses compact rails independently and resets on media changes", () => {
    const root = railRoot();
    const drawer = mediaQuery(false);
    const compact = mediaQuery(true);
    const rails = new ResponsiveRails(root, { drawer, compact });
    const scopeButton = button(root, "scope");
    const inspectorButton = button(root, "inspector");

    expect(scopeButton.getAttribute("aria-expanded")).toBe("true");
    scopeButton.click();
    inspectorButton.click();
    expect(root.classList.contains("is-scope-collapsed")).toBe(true);
    expect(root.classList.contains("is-inspector-collapsed")).toBe(true);

    rails.open("scope");
    expect(root.classList.contains("is-scope-collapsed")).toBe(false);
    expect(root.classList.contains("is-inspector-collapsed")).toBe(true);

    compact.change(false);
    expect(root.classList.contains("is-inspector-collapsed")).toBe(false);
    expect(inspectorButton.getAttribute("aria-expanded")).toBe("true");
    rails.toggle("inspector");
    expect(inspectorButton.getAttribute("aria-expanded")).toBe("true");
    rails.dispose();
  });

  it("creates browser media queries and tolerates absent panels", () => {
    const wide = mediaQuery(false);
    const matchMedia = vi.fn(() => wide);
    vi.stubGlobal("matchMedia", matchMedia);
    const root = document.createElement("main");

    const rails = new ResponsiveRails(root);
    rails.open("scope");

    expect(matchMedia).toHaveBeenCalledTimes(2);
    rails.dispose();
    vi.unstubAllGlobals();
  });
});

function railRoot() {
  const root = document.createElement("main");
  root.insertAdjacentHTML(
    "beforeend",
    "<button data-rail-action='scope'></button>" +
      "<button data-rail-action='inspector'></button>" +
      "<aside data-scope-navigator></aside>" +
      "<aside data-image-inspector></aside>",
  );
  document.body.append(root);
  return root;
}

function button(root, rail) {
  return /** @type {HTMLButtonElement} */ (
    root.querySelector(`[data-rail-action='${rail}']`)
  );
}

function panel(root, selector) {
  return /** @type {HTMLElement} */ (root.querySelector(selector));
}

function mediaQuery(matches) {
  const listeners = new Set();
  return {
    matches,
    addEventListener: (_type, listener) => listeners.add(listener),
    removeEventListener: (_type, listener) => listeners.delete(listener),
    change(next) {
      this.matches = next;
      for (const listener of listeners) listener(new Event("change"));
    },
  };
}
