import { beforeEach, describe, expect, it, vi } from "vitest";

import { CatalogBrowser } from "../../static/js/catalog/catalog-browser.js";
import { CatalogEditor } from "../../static/js/catalog/catalog-editor.js";
import { CatalogEvidenceView } from "../../static/js/catalog/catalog-evidence-view.js";

const components = [
  component("character-a", "character", "Aiko", false, ["hero"]),
  component("scene-a", "scene", "Rainy Street", true, ["rain"]),
];

describe("Catalog browser components", () => {
  beforeEach(() => document.body.replaceChildren());

  it("filters searchable catalog entries and owns selection listeners", () => {
    const kinds = document.createElement("nav");
    const list = document.createElement("div");
    const search = document.createElement("input");
    const onSelect = vi.fn();
    const browser = new CatalogBrowser(kinds, list, search, { onSelect });

    browser.render(components);
    expect(list.querySelectorAll(".catalog-item")).toHaveLength(2);
    kinds.querySelectorAll("button")[2].click();
    expect(list.querySelectorAll(".catalog-item")).toHaveLength(1);
    list.querySelector("button").click();
    expect(onSelect).toHaveBeenCalledWith("scene-a");

    browser.select("scene-a");
    expect(list.querySelector("button").getAttribute("aria-current")).toBe(
      "true",
    );
    search.value = "nicht vorhanden";
    search.dispatchEvent(new Event("input"));
    expect(list.textContent).toContain("Keine Einträge");
    browser.dispose();
  });

  it("creates, edits, archives and renders immutable history", () => {
    const root = document.createElement("div");
    const onSave = vi.fn();
    const onArchive = vi.fn();
    const editor = new CatalogEditor(root, {
      onSave,
      onArchive,
      onEvidenceOpen: vi.fn(),
    });

    editor.create();
    const createInputs = root.querySelectorAll("input");
    createInputs[0].value = "Neue Szene";
    createInputs[1].value = "rain, night";
    root.querySelector(".prompt-atom-editor > button").click();
    const positiveText = root.querySelectorAll("[data-atom-text]")[0];
    positiveText.value = "rainy street";
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "scene",
        name: "Neue Szene",
        tags: ["rain", "night"],
        positive_atoms: [{ text: "rainy street", weight: 1 }],
      }),
    );

    editor.render(components[1], [revision(1), revision(2)]);
    expect(root.querySelectorAll(".catalog-revision")).toHaveLength(2);
    expect(
      root.querySelector(".catalog-rendered-snapshots").textContent,
    ).toContain("positive 2");
    expect(root.querySelector("select").disabled).toBe(true);
    root.querySelector(".archive-button").click();
    expect(onArchive).toHaveBeenCalledWith(false);
    editor.setBusy(true);
    expect(root.querySelector("input").disabled).toBe(true);
    editor.setBusy(false);
    expect(root.querySelector("select").disabled).toBe(true);
    editor.dispose();
  });

  it("shows at most three lazy evidence images and owns interactions", () => {
    const onOpen = vi.fn();
    const view = new CatalogEvidenceView({ onOpen });
    const images = Array.from({ length: 4 }, (_, index) => ({
      image_uid: `image-${index}`,
      image_url: `/output/image-${index}.png`,
      average_rating: index === 0 ? 9.5 : null,
      rating_count: index,
    }));

    view.render(images);
    expect(view.element.querySelectorAll("img")).toHaveLength(3);
    expect(view.element.querySelector("img").loading).toBe("lazy");
    expect(view.element.textContent).toContain("Ø 9,5 / 10");
    view.element.querySelector("button").click();
    expect(onOpen).toHaveBeenCalledWith("image-0", "/output/image-0.png");

    view.render([]);
    expect(view.element.textContent).toContain("Noch keine");
    view.dispose();
    expect(view.element.childElementCount).toBe(0);
  });
});

function component(componentUid, kind, name, archived, tags) {
  return {
    component_uid: componentUid,
    component_key: `${kind}-key`,
    kind,
    name,
    tags,
    notes: "notes",
    archived,
    latest_revision: revision(2),
  };
}

function revision(number) {
  return {
    revision_uid: `revision-${number}`,
    revision_number: number,
    positive_text: `positive ${number}`,
    negative_text: "",
    positive_atoms: [{ text: `positive ${number}`, weight: 1 }],
    negative_atoms: [],
  };
}
