import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImageGrid } from "../../static/js/images/image-grid.js";
import { ImageViewer } from "../../static/js/images/image-viewer.js";
import { PaginationControls } from "../../static/js/images/pagination-controls.js";
import { ImageInspector } from "../../static/js/inspector/image-inspector.js";
import { ActiveScopeChips } from "../../static/js/scopes/active-scope-chips.js";
import { ScopeNavigator } from "../../static/js/scopes/scope-navigator.js";

describe("V2 view components", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("renders scope facets as text and owns filter events", () => {
    const root = document.createElement("aside");
    document.body.append(root);
    const onToggle = vi.fn();
    const onClassification = vi.fn();
    const navigator = new ScopeNavigator(root, { onToggle, onClassification });

    navigator.render(
      [
        {
          kind: "character",
          component_uid: "character-a",
          name: "<Aiko>",
          count: 12,
          archived: true,
        },
      ],
      ["character-a"],
      "classified",
    );
    root.querySelector("button")?.click();
    const select = root.querySelector("select");
    select.value = "unclassified";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    expect(root.textContent).toContain("<Aiko>");
    expect(root.querySelector("button")?.getAttribute("aria-pressed")).toBe(
      "true",
    );
    expect(onToggle).toHaveBeenCalledWith("character-a");
    expect(onClassification).toHaveBeenCalledWith("unclassified");
    navigator.dispose();
    root.querySelector("button")?.click();
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("renders image cards, status states, and delegated actions", () => {
    const root = document.createElement("div");
    document.body.append(root);
    const onSelect = vi.fn();
    const onExpand = vi.fn();
    const grid = new ImageGrid(root, { onSelect, onExpand });
    const item = {
      image_uid: "image-1",
      image_url: "/files/image-1.png",
      review_summary: { average_rating: 8.25, rating_count: 3 },
      scopes: [{ kind: "character", name: "Aiko" }],
    };

    grid.loading();
    expect(root.textContent).toContain("geladen");
    grid.render([item], 4);
    root
      .querySelector("[data-image-action='select']")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    root
      .querySelector("[data-image-action='expand']")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(root.textContent).toContain("#5");
    expect(root.textContent).toContain("Ø 8,3 / 10");
    expect(onSelect).toHaveBeenCalledWith("image-1");
    expect(onExpand).toHaveBeenCalledWith("image-1", "/files/image-1.png");
    grid.render([], 0);
    expect(root.textContent).toContain("Keine Bilder");
    grid.error("");
    expect(root.textContent).toContain("konnten nicht");
    grid.dispose();
  });

  it("renders image details and each inspector status", () => {
    const root = document.createElement("aside");
    const inspector = new ImageInspector(root);
    const image = {
      image_uid: "image-1",
      generation_uid: "generation-1",
      image_url: "/files/image.png",
      review_summary: { average_rating: 9, rating_count: 2 },
      scopes: [{ kind: "outfit", name: "Sommerkleid" }],
      prompt_snapshot: {
        positive: "portrait",
        negative: "blur",
        draft_overridden: true,
      },
    };

    inspector.empty();
    expect(root.textContent).toContain("Wähle");
    inspector.loading();
    expect(root.textContent).toContain("geladen");
    inspector.error("");
    expect(root.textContent).toContain("konnten nicht");
    inspector.render(image);

    expect(root.textContent).toContain("Ø 9,0 / 10 · 2×");
    expect(root.textContent).toContain("Draft-Override");
    expect(root.querySelector("img")?.src).toContain("/files/image.png");
  });

  it("opens, closes, and disposes the image viewer", () => {
    const dialog = document.createElement("dialog");
    const close = document.createElement("button");
    close.dataset.viewerClose = "";
    const image = document.createElement("img");
    dialog.append(close, image);
    document.body.append(dialog);
    dialog.showModal = vi.fn(() => dialog.setAttribute("open", ""));
    dialog.close = vi.fn(() => dialog.removeAttribute("open"));
    const viewer = new ImageViewer(dialog);

    viewer.open("");
    expect(dialog.showModal).not.toHaveBeenCalled();
    viewer.open("/files/image.png");
    close.click();
    expect(dialog.showModal).toHaveBeenCalledOnce();
    expect(dialog.close).toHaveBeenCalledOnce();
    expect(image.hasAttribute("src")).toBe(false);
    viewer.dispose();

    const invalid = document.createElement("dialog");
    expect(() => new ImageViewer(invalid)).toThrow("img element");
  });

  it("renders active scopes and owns removal actions", () => {
    const root = document.createElement("div");
    const onRemove = vi.fn();
    const onClear = vi.fn();
    const chips = new ActiveScopeChips(root, { onRemove, onClear });

    chips.render([], []);
    expect(root.hidden).toBe(true);
    chips.render(
      [{ component_uid: "character-a", name: "<Aiko>" }],
      ["character-a", "unknown"],
    );
    expect(root.hidden).toBe(false);
    expect(root.textContent).toContain("<Aiko>");
    root
      .querySelector("[data-scope-uid='character-a']")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    root
      .querySelector("[data-active-scope-action='clear']")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onRemove).toHaveBeenCalledWith("character-a");
    expect(onClear).toHaveBeenCalledOnce();
    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    const unknown = document.createElement("button");
    unknown.dataset.activeScopeAction = "unknown";
    root.append(unknown);
    unknown.click();
    chips.dispose();
  });

  it("renders bounded page navigation and ignores disabled actions", () => {
    const root = document.createElement("nav");
    const onPage = vi.fn();
    const pagination = new PaginationControls(root, { onPage });

    pagination.render(10, 0, 48);
    expect(root.hidden).toBe(true);
    pagination.render(100, 48, 48);
    expect(root.textContent).toContain("49–96 von 100");
    const buttons = root.querySelectorAll("button");
    buttons[0].click();
    buttons[1].click();
    expect(onPage).toHaveBeenNthCalledWith(1, 0);
    expect(onPage).toHaveBeenNthCalledWith(2, 96);
    pagination.render(100, 96, 48);
    root.querySelectorAll("button")[1].click();
    expect(onPage).toHaveBeenCalledTimes(2);
    pagination.render(0, 48, 48);
    expect(root.textContent).toContain("0–0 von 0");
    root.click();
    const textTarget = document.createTextNode("text");
    root.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    pagination.dispose();
  });
});
