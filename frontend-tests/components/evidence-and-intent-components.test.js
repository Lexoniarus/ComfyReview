import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvidenceCarousel } from "../../static/js/components/evidence-carousel.js";
import { ImageGeneratorActions } from "../../static/js/images/image-generator-actions.js";

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

  it("owns consistent direct image handoff actions and disposal", () => {
    const navigator = { openIntent: vi.fn() };
    const actions = new ImageGeneratorActions(navigator);
    const compact = actions.create("image-1");
    document.body.append(compact);
    const toggle = compact.querySelector(".image-generator-actions-toggle");
    toggle.click();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    compact.querySelector("[data-playground-intent='prompt']").click();
    expect(navigator.openIntent).toHaveBeenCalledWith({
      kind: "image-prompt",
      imageUid: "image-1",
    });
    expect(compact.textContent).toContain("Prompt & LoRAs übernehmen");

    const prominent = actions.create("image-2", "prominent");
    prominent.querySelector("[data-playground-intent='render']").click();
    expect(navigator.openIntent).toHaveBeenCalledWith({
      kind: "image-render",
      imageUid: "image-2",
    });
    expect(prominent.textContent).toContain(
      "Generierungseinstellungen übernehmen",
    );
    actions.dispose();
    compact.querySelector("[data-playground-intent='prompt']").click();
    expect(navigator.openIntent).toHaveBeenCalledTimes(2);
  });
});

function pointerEvent(type, clientX) {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "clientX", { value: clientX });
  return event;
}
