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
    expect(browser.selectedCatalogKind()).toBe("component");
    expect(list.querySelectorAll(".catalog-item")).toHaveLength(2);
    kinds.querySelectorAll("button")[2].click();
    expect(list.querySelectorAll(".catalog-item")).toHaveLength(1);
    list.querySelector("button").click();
    expect(onSelect).toHaveBeenCalledWith("scene-a", "component");

    browser.select("scene-a");
    expect(list.querySelector("button").getAttribute("aria-current")).toBe(
      "true",
    );
    search.value = "nicht vorhanden";
    search.dispatchEvent(new Event("input"));
    expect(list.textContent).toContain("Keine Einträge");
    kinds.querySelectorAll("button").item(12).click();
    expect(browser.selectedCatalogKind()).toBe("lora");
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
    button(root, "Atom hinzufügen").click();
    const positiveText = root.querySelectorAll("[data-atom-text]")[0];
    positiveText.value = "rainy street";
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "scene",
        name: "Neue Szene",
        content_level: "standard",
        tags: ["rain", "night"],
        positive_atoms: [{ text: "rainy street", weight: 1 }],
      }),
    );

    editor.render({ ...components[1], current_revision: revision(1) }, [
      revision(1),
      revision(2),
    ]);
    expect(root.querySelectorAll(".catalog-revision")).toHaveLength(2);
    expect(
      root.querySelector(".catalog-rendered-snapshots").textContent,
    ).toContain("positive 1");
    expect(root.querySelector("[data-atom-text]").value).toBe("positive 1");
    expect(root.querySelector("select").disabled).toBe(true);
    root.querySelector(".archive-button").click();
    expect(onArchive).toHaveBeenCalledWith(false);
    editor.setBusy(true);
    expect(root.querySelector("input").disabled).toBe(true);
    editor.setBusy(false);
    expect(root.querySelector("select").disabled).toBe(true);
    editor.dispose();
  });

  it("creates and revises LoRAs through the canonical catalog editor", () => {
    const root = document.createElement("div");
    const onSave = vi.fn();
    const onArchive = vi.fn();
    const editor = new CatalogEditor(root, {
      onSave,
      onArchive,
      onEvidenceOpen: vi.fn(),
    });

    editor.create("lora");
    const inputs = root.querySelectorAll("input");
    inputs[0].value = "Anime Style";
    inputs[1].value = "anime-style.safetensors";
    inputs[2].value = "style, anime";
    inputs[3].value = "0.8";
    inputs[4].value = "0.65";
    button(root, "Atom hinzufügen").click();
    root.querySelector("[data-atom-text]").value = "anime trigger";
    root
      .querySelector("form")
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        catalog_kind: "lora",
        provider_name: "anime-style.safetensors",
        display_name: "Anime Style",
        tags: ["style", "anime"],
        default_model_strength: 0.8,
        default_clip_strength: 0.65,
        positive_atoms: [{ text: "anime trigger", weight: 1 }],
      }),
    );

    const lora = {
      catalog_kind: "lora",
      lora_uid: "lora-style",
      provider_name: "anime-style.safetensors",
      display_name: "Anime Style",
      content_level: "sexy",
      tags: ["anime"],
      notes: "Curated",
      revision: 2,
      archived: false,
      latest_revision: {
        ...revision(2),
        default_model_strength: 0.9,
        default_clip_strength: 0.7,
      },
    };
    editor.render(lora, [lora.latest_revision]);
    expect(root.textContent).toContain("LoRA-Katalog");
    expect(root.querySelectorAll(".catalog-revision")).toHaveLength(1);
    root.querySelector(".archive-button").click();
    expect(onArchive).toHaveBeenCalledWith(true);
    editor.setBusy(true);
    expect(root.querySelector("input").disabled).toBe(true);
    editor.dispose();
  });

  it("shows all evidence through one cyclic lazy image and owns interactions", () => {
    const onOpen = vi.fn();
    const view = new CatalogEvidenceView({ onOpen });
    const images = Array.from({ length: 4 }, (_, index) => ({
      image_uid: `image-${index}`,
      image_url: `/output/image-${index}.png`,
      average_rating: index === 0 ? 9.5 : null,
      rating_count: index,
    }));

    view.render(images);
    expect(view.element.querySelectorAll("img")).toHaveLength(1);
    expect(
      view.element.querySelector(".catalog-evidence-strip").dataset.count,
    ).toBe("4");
    expect(view.element.querySelector("img").loading).toBe("lazy");
    expect(view.element.textContent).toContain("Ø 9,5 / 10");
    view.element.querySelector(".evidence-carousel-image").click();
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
    content_level: "sexy",
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

function button(root, label) {
  return [...root.querySelectorAll("button")].find(
    (candidate) => candidate.textContent === label,
  );
}
