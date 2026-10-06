import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlaygroundIntentTray } from "../../static/js/analytics/playground-intent-tray.js";
import { EvidenceCarousel } from "../../static/js/components/evidence-carousel.js";
import { ImageGeneratorActions } from "../../static/js/images/image-generator-actions.js";
import { PlaygroundIntentStore } from "../../static/js/playground/playground-intent.js";

describe("Shared evidence and Playground intent components", () => {
  beforeEach(() => {
    document.body.replaceChildren();
    vi.useFakeTimers();
  });

  afterEach(() => vi.useRealTimers());

  it("owns a cyclic evidence carousel across every input method", () => {
    const selected = vi.fn();
    const createGeneratorActions = vi.fn(() => document.createElement("menu"));
    const carousel = new EvidenceCarousel({
      onSelect: selected,
      className: "analytics-image-strip",
      createGeneratorActions,
    });
    expect(carousel.render([], "Leer").textContent).toContain(
      "Kein Bildbeispiel",
    );

    const root = carousel.render(
      [
        {
          image_uid: "one",
          image_url: "/one.png",
          average_rating: 8.5,
          rating_count: 3,
        },
        { image_uid: "two", url: "/two.png", rating_count: 0 },
      ],
      "Beleg",
    );
    document.body.append(root);
    expect(createGeneratorActions).toHaveBeenCalledWith("one");
    const imageButton = root.querySelector(".evidence-carousel-image");
    const image = root.querySelector("img");
    imageButton.click();
    expect(selected).toHaveBeenCalledWith(
      expect.objectContaining({ image_uid: "one" }),
    );
    root.querySelector(".is-next").click();
    expect(image.getAttribute("src")).toBe("/two.png");
    expect(createGeneratorActions).toHaveBeenLastCalledWith("two");
    root.querySelector(".is-previous").click();
    expect(image.getAttribute("src")).toBe("/one.png");

    root.dispatchEvent(new WheelEvent("wheel", { deltaX: 0, deltaY: 40 }));
    expect(image.getAttribute("src")).toBe("/one.png");
    root.dispatchEvent(
      new WheelEvent("wheel", {
        bubbles: true,
        cancelable: true,
        deltaX: 40,
        deltaY: 0,
      }),
    );
    expect(image.getAttribute("src")).toBe("/two.png");
    root.dispatchEvent(pointerEvent("pointerdown", 100));
    root.dispatchEvent(pointerEvent("pointerup", 50));
    expect(image.getAttribute("src")).toBe("/one.png");
    root.dispatchEvent(pointerEvent("pointerdown", 50));
    root.dispatchEvent(pointerEvent("pointerup", 100));
    expect(image.getAttribute("src")).toBe("/two.png");
    root.dispatchEvent(pointerEvent("pointerdown", 50));
    root.dispatchEvent(pointerEvent("pointerup", 60));
    expect(image.getAttribute("src")).toBe("/two.png");
    image.dispatchEvent(new Event("error"));
    expect(imageButton.dataset.state).toBe("failed");
    carousel.dispose();

    const defaultCarousel = new EvidenceCarousel();
    const withoutRating = defaultCarousel.render(
      [{ image_url: "/only.png" }],
      "Ein Bild",
    );
    expect(withoutRating.querySelector(".evidence-carousel-meta").hidden).toBe(
      true,
    );
    withoutRating.querySelector("button").click();
    defaultCarousel.dispose();

    const isolatedCarousel = new EvidenceCarousel({ isolateGestures: true });
    const isolated = isolatedCarousel.render(
      [{ url: "/one.png" }, { url: "/two.png" }],
      "Isoliert",
    );
    const outer = document.createElement("div");
    const outerEvent = vi.fn();
    outer.addEventListener("pointerup", outerEvent);
    outer.addEventListener("wheel", outerEvent);
    outer.addEventListener("touchmove", outerEvent);
    outer.append(isolated);
    isolated.dispatchEvent(
      new WheelEvent("wheel", { bubbles: true, deltaX: 40, deltaY: 0 }),
    );
    isolated.dispatchEvent(pointerEvent("pointerdown", 100));
    isolated.dispatchEvent(pointerEvent("pointerup", 50));
    isolated.dispatchEvent(new Event("touchmove", { bubbles: true }));
    expect(outerEvent).not.toHaveBeenCalled();
    isolatedCarousel.dispose();
  });

  it("stages, summarizes, resets and consumes tab-local intents", () => {
    const storage = new MemoryStorage();
    const store = new PlaygroundIntentStore(storage);
    const root = document.createElement("aside");
    const toast = document.createElement("div");
    const locationRef = { assign: vi.fn() };
    const tray = new PlaygroundIntentTray(root, toast, store, locationRef);
    expect(root.hidden).toBe(true);
    root.append(document.createElement("span"));
    root.firstElementChild.click();
    tray.notify("Direkte Nachricht");
    expect(toast.textContent).toBe("Direkte Nachricht");

    tray.stage(
      action("scope", {
        componentUid: "character-a",
        promptKind: "character",
      }),
    );
    expect(root.textContent).toContain("Prompt-Baustein");
    expect(toast.textContent).toContain("Prompt");
    tray.stage(action("parameter", { parameter: "cfg", value: "6.5" }));
    expect(root.textContent).toContain("CFG 6.5");
    expect(toast.textContent).toContain("cfg");
    tray.stage(
      action("recommendation", {
        recommendation: JSON.stringify({
          checkpoint: "model",
          sampler: "euler",
          scheduler: "normal",
          steps: 24,
          cfg: 6,
          denoise: 1,
        }),
      }),
    );
    expect(root.textContent).toContain("Checkpoint model");
    expect(toast.textContent).toContain("Gesamtsetup");
    tray.stage(
      action("composition", {
        compositionUid: "composition-a",
        componentUids: "[]",
      }),
    );
    expect(root.textContent).toContain("Prompt-Komposition");
    tray.stage(action("scope", { componentUids: '["character-a","scene-a"]' }));
    expect(root.textContent).toContain("2 Prompt-Baustein(e)");
    store.merge({ compositionUid: "legacy-composition" });
    tray.render();
    expect(root.textContent).toContain("Prompt-Komposition");
    tray.stage(action("image", { imageUid: "image-a" }));
    expect(toast.textContent).toContain("Auswahl");

    root.querySelector("[data-intent-open]").click();
    expect(locationRef.assign).toHaveBeenCalledWith(
      expect.stringContaining("/playground/generator?"),
    );
    tray.render();
    expect(root.hidden).toBe(false);
    store.clear();
    tray.render();
    expect(root.hidden).toBe(true);

    tray.stage(action("parameter", { parameter: "sampler", value: "euler" }));
    root.querySelector("[data-intent-reset]").click();
    expect(root.hidden).toBe(true);
    tray.stage(action("parameter", { parameter: "steps", value: "20" }));
    vi.runAllTimers();
    expect(toast.hidden).toBe(true);
    tray.stage(action("parameter", { parameter: "cfg", value: "7" }));
    tray.dispose();
  });

  it("owns image handoff menus, validation, notifications and disposal", async () => {
    const promptSetup = {
      selections: [
        {
          kind: "character",
          component_uid: "character-a",
          revision_uid: "character-rev-1",
          position: 0,
        },
        {
          kind: "scene",
          component_uid: "scene-a",
          revision_uid: "scene-rev-1",
          position: 1,
        },
      ],
      loras: [],
    };
    const api = {
      get: vi.fn(async () => ({
        prompt_setup: promptSetup,
        render_setup: { applicable: true },
      })),
    };
    const store = {
      stagePromptImage: vi.fn(),
      stageRenderSetup: vi.fn(),
    };
    const eventTarget = new EventTarget();
    const notifications = [];
    eventTarget.addEventListener("comfyreview:intent-staged", (event) =>
      notifications.push(event.detail.message),
    );
    const actions = new ImageGeneratorActions({ api, store, eventTarget });
    const compact = actions.create("image-1");
    document.body.append(compact);
    const toggle = compact.querySelector(".image-generator-actions-toggle");
    toggle.click();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    compact.querySelector(".secondary-button").click();
    await settle();
    expect(store.stagePromptImage).toHaveBeenCalledWith("image-1");
    expect(notifications.at(-1)).toContain("Prompt-Setup");

    const prominent = actions.create("image-2", "prominent");
    prominent.querySelector(".ghost-button").click();
    await settle();
    expect(store.stageRenderSetup).toHaveBeenCalledWith("image-2");

    api.get.mockResolvedValueOnce({
      render_setup: { applicable: false, issues: ["multi_stage"] },
    });
    prominent.querySelector(".ghost-button").click();
    await settle();
    expect(notifications.at(-1)).toContain("multi_stage");
    api.get.mockRejectedValueOnce(new Error("kaputt"));
    prominent.querySelector(".secondary-button").click();
    await settle();
    expect(notifications.at(-1)).toBe("kaputt");
    api.get.mockResolvedValueOnce({
      prompt_setup: {
        selections: [],
        component_uids: ["legacy-character"],
        revision_uids: ["legacy-revision"],
      },
      render_setup: { applicable: true },
    });
    prominent.querySelector(".secondary-button").click();
    await settle();
    expect(notifications.at(-1)).toContain("Character-Prompt-Setup");
    api.get.mockRejectedValueOnce(new DOMException("aborted", "AbortError"));
    prominent.querySelector(".secondary-button").click();
    await settle();
    actions.dispose();
  });
});

class MemoryStorage {
  constructor() {
    this.values = new Map();
  }

  getItem(key) {
    return this.values.get(key) ?? null;
  }

  setItem(key, value) {
    this.values.set(key, String(value));
  }

  removeItem(key) {
    this.values.delete(key);
  }
}

function action(kind, values) {
  const element = document.createElement("button");
  element.dataset.playgroundIntent = kind;
  Object.assign(element.dataset, values);
  return element;
}

function pointerEvent(type, clientX) {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "clientX", { value: clientX });
  return event;
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
}
