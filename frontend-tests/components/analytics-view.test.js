import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsView } from "../../static/js/analytics/focused-analytics-view.js";
import { AnalyticsCardRail } from "../../static/js/analytics/analytics-card-rail.js";
import {
  emptyMessage,
  sectionTitle,
  settingLine,
} from "../../static/js/analytics/analytics-formatters.js";
import { EvidenceImageStrip } from "../../static/js/analytics/evidence-image-strip.js";

describe("AnalyticsView", () => {
  beforeEach(() => document.body.replaceChildren());

  it("renders coverage without mixing recommendations into the overview", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);
    view.render("overview", {
      active_image_count: 377,
      rated_image_count: 370,
      observed_setup_count: 130,
      stable_setup_count: 9,
      prompt_linked_image_count: 300,
      unlinked_prompt_image_count: 77,
      legacy_image_count: 12,
      geometry_projected_count: 377,
      modeled_value_counts: { sampler: 5, steps: 15 },
      geometry_value_counts: [
        { dimension: "aspect_format", value: "1:1", image_count: 152 },
      ],
    });
    expect(root.textContent).toContain("130");
    expect(root.textContent).toContain("ausreichend gesichtet");
    expect(root.textContent).not.toContain("Vermeiden");
    expect(root.textContent).toContain("Format 1:1152Bilder");
    expect(root.querySelectorAll(".analytics-card-rail")).toHaveLength(3);
    view.overview.metrics.carousel.currentIndex = 99;
    view.overview.metrics.carousel.refresh();
    expect(view.overview.metrics.carousel.currentIndex).toBe(0);
  });

  it("owns empty and interrupted card-rail gestures safely", () => {
    const rail = new AnalyticsCardRail("test-track");
    document.body.append(rail.element);

    rail.carousel.move(1);
    const plainText = document.createTextNode("plain");
    rail.element.append(plainText);
    plainText.dispatchEvent(new Event("click", { bubbles: true }));
    rail.track.dispatchEvent(touchEvent("touchmove", []));
    rail.track.dispatchEvent(
      touchEvent("touchstart", [{ clientX: 80, clientY: 0 }]),
    );
    rail.track.dispatchEvent(touchEvent("touchmove", []));

    rail.dispose();
  });

  it("renders catalog scope evidence as one large cyclic viewer", () => {
    const root = document.createElement("div");
    const open = vi.fn();
    const view = new AnalyticsView(root, { onImageSelect: open });
    view.render("scopes", {
      kind: "character",
      items: [
        {
          kind: "character",
          component_uid: "character-a",
          name: "Aiko <script>",
          image_count: 2,
          rating_count: 3,
          average_rating: 8.5,
          best_images: [
            { image_uid: "image-1", url: "/one.png", avg_rating: 9 },
            { image_uid: "image-2", url: "/two.png", avg_rating: 8 },
          ],
        },
      ],
    });
    expect(root.querySelector("script")).toBeNull();
    expect(root.querySelector(".analytics-image-strip")?.dataset.count).toBe(
      "2",
    );
    root
      .querySelector(".evidence-carousel-image")
      ?.dispatchEvent(new Event("click"));
    expect(open).toHaveBeenCalledWith("image-1", "/one.png");
    expect(root.textContent).toContain("Prompt & LoRAs übernehmen");
  });

  it("renders every observed/predicted setup/parameter mode with concrete support", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);
    view.render("parameters", {
      basis: "predicted",
      scope: "parameter",
      parameter: "sampler",
      total: 2,
      filtered_total: 1,
      coverage: { observed_setup_count: 130, stable_setup_count: 9 },
      items: [
        {
          parameter: "sampler",
          value: "euler",
          applicable: true,
          predicted: {
            expected_success_rate: 0.82,
            image_count: 14,
            review_count: 20,
            confidence: "medium",
            relative_rank: 1,
          },
        },
      ],
    });
    expect(root.textContent).toContain("Rechnerisch");
    expect(root.textContent).toContain("82.0 % prognostizierter Erfolg");
    expect(root.textContent).toContain("14 unabhängige Bilder");
    expect(root.textContent).toContain("Parameter übernehmen");
    expect(root.querySelectorAll("[data-guidance-basis]")).toHaveLength(2);
    expect(
      root.querySelectorAll("[data-guidance-scope]").length,
    ).toBeGreaterThan(2);
  });

  it("keeps combinations prompt-only and renders focused setup details separately", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);
    view.render("combinations", {
      items: [
        {
          composition_uid: "composition-a",
          component_names: ["Aiko", "Rooftop"],
          component_uids: ["character-a", "scene-a"],
          image_count: 2,
          rating_count: 3,
          average_rating: 8.5,
        },
      ],
    });
    expect(root.textContent).toContain("Prompt & LoRAs übernehmen");
    expect(root.querySelector("[data-analytics-view]")).toBeNull();
    view.renderCompositionSetups("composition-a", {
      rows: [
        {
          setup_key: "setup-a",
          checkpoint: "model.safetensors",
          stages: [
            {
              sampler: "euler",
              scheduler: "normal",
              steps: 24,
              cfg: 6.5,
              denoise: 1,
            },
          ],
          image_count: 2,
          rating_count: 3,
        },
      ],
    });
    expect(root.textContent).toContain("model.safetensors");
  });

  it("covers empty, archived, setup and incremental analytics states", () => {
    expect(
      settingLine({ sampler: "euler", scheduler: "normal", steps: 20, cfg: 6 }),
    ).toContain("20 Steps");
    expect(sectionTitle("Abschnitt").textContent).toBe("Abschnitt");
    expect(emptyMessage("Leer").className).toBe("analytics-empty");

    const root = document.createElement("div");
    const view = new AnalyticsView(root);
    view.render("scopes", { items: [] });
    expect(root.textContent).toContain("Keine Scopes");
    view.append({
      items: [
        {
          kind: "outfit",
          component_uid: "outfit-a",
          name: "Archiviert",
          archived: true,
          best_images: [],
        },
      ],
    });
    expect(root.textContent).toContain("Archiviert");

    view.render("parameters", {
      basis: "observed",
      scope: "setup",
      items: [],
      coverage: {},
    });
    expect(root.textContent).toContain("Keine Evidenz");
    view.append({
      items: [
        {
          applicable: false,
          settings: {
            checkpoint: "model",
            sampler: "euler",
            scheduler: "normal",
            steps: 20,
            cfg: 6,
            denoise: 1,
          },
          evidence: {
            expected_success_rate: 0.5,
            image_count: 2,
            review_count: 2,
            confidence: "insufficient",
            relative_rank: 0,
          },
          best_images: [],
        },
      ],
    });
    expect(root.textContent).toContain("Generierungseinstellungen übernehmen");
    view.render("parameters", {
      basis: "predicted",
      scope: "setup",
      items: [
        {
          applicable: true,
          settings: { checkpoint: "predicted-model" },
          evidence: {},
        },
      ],
      coverage: {},
    });
    expect(
      root.querySelector("[data-playground-intent='recommendation']"),
    ).not.toBeNull();

    view.render("combinations", { items: [] });
    expect(root.textContent).toContain("Keine Kombinationen");
    view.append({
      items: [
        {
          composition_uid: "composition-empty",
          component_names: [],
          component_uids: [],
        },
      ],
    });
    view.renderCompositionSetups("missing", { rows: [] });
    view.renderCompositionSetups("composition-empty", { rows: [] });
    expect(root.textContent).toContain("Keine technischen Setups");
    view.renderCompositionSetups("composition-empty", { rows: [] });
    view.dispose();
    expect(root.children).toHaveLength(0);

    const images = new EvidenceImageStrip();
    const image = images.render(
      [{ image_uid: "image", url: "/image.png" }],
      "Bild",
    );
    image.querySelector("button").click();
    images.dispose();
  });
});

function touchEvent(type, touches) {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "touches", { value: touches });
  return event;
}
