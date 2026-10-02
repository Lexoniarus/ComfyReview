import { beforeEach, describe, expect, it, vi } from "vitest";

import { AnalyticsView } from "../../static/js/analytics/focused-analytics-view.js";

describe("AnalyticsView", () => {
  beforeEach(() => document.body.replaceChildren());

  it("renders overview evidence safely", () => {
    const { root, view } = fixture();
    view.render("overview", {
      stable: [
        {
          checkpoint: "Aiko <script>",
          n: 4,
          avg_rating: 8.5,
        },
      ],
      avoid: [],
      approx: {
        base: { n: 40 },
        rows: [
          {
            sampler: "euler",
            scheduler: "normal",
            steps: 30,
            cfg: 6.5,
            pred_success: 0.8,
          },
        ],
      },
    });

    expect(root.textContent).toContain("Aiko <script>");
    expect(root.querySelector("script")).toBeNull();
    expect(root.textContent).toContain("euler · normal · 30 Steps");
    expect(root.textContent).toContain("Keine Einträge");

    view.render("overview", { stable: [], avoid: [], approx: null });
    expect(root.textContent).toContain("Keine rechnerischen Kandidaten");

    view.render("scopes", {
      items: [
        {
          component_uid: "default-action",
          name: "Default action",
          best_images: [{ image_uid: "image-default", url: "default.png" }],
        },
      ],
    });
    root.querySelector(".analytics-image-button")?.click();
  });

  it("renders canonical scope groups and explicit empty states", () => {
    const onImageSelect = vi.fn();
    const { root, view } = fixture({ onImageSelect });
    view.render("scopes", {
      kind: "character",
      items: [
        {
          kind: "character",
          name: "Aiko",
          archived: true,
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
          best_images: [
            { image_uid: "image-a", url: "image.png", avg_rating: 9 },
            { url: "", avg_rating: 8 },
          ],
        },
        { kind: "unknown", name: "Ignored" },
      ],
    });

    expect(root.textContent).toContain("Charakter");
    expect(root.textContent).toContain("Aiko");
    expect(root.textContent).toContain("Archiviert");
    expect(root.querySelector("img")?.loading).toBe("lazy");
    expect(root.querySelector(".analytics-image-strip")?.dataset.count).toBe(
      "1",
    );
    root.querySelector(".analytics-image-button")?.click();
    expect(onImageSelect).toHaveBeenCalledWith("image-a");
    root.querySelector("img")?.dispatchEvent(new Event("error"));
    expect(root.querySelector(".analytics-image-button")?.dataset.state).toBe(
      "failed",
    );
    view.append({
      items: [
        {
          kind: "character",
          component_uid: "component-b",
          name: "Kaori",
        },
      ],
    });

    view.render("scopes", { kind: "character", items: null });
    expect(root.textContent).toContain("Keine Scopes");
  });

  it("keeps calculated, observed, and selected parameter evidence separate", () => {
    const { root, view } = fixture();
    view.render("parameters", {
      view: "summary",
      recommendations: [
        {
          checkpoint: "model.safetensors",
          sampler: "euler",
          scheduler: "normal",
          steps: 30,
          cfg: 6.5,
          score: 0.7,
          checkpoint_lower_bound: 0.6,
        },
      ],
      items: [setup()],
    });

    expect(root.textContent).toContain("nicht gemeinsam getestet");
    expect(root.textContent).toContain("base · euler / normal");
    expect(root.querySelectorAll("[data-analytics-view]")).toHaveLength(6);

    view.render("parameters", {
      view: "values",
      parameter: "steps",
      items: [
        {
          value: "30",
          sample_count: 5,
          average_rating: 8,
          expected_success_rate: 0.7,
          lower_bound: 0.6,
          best_images: [{ url: "best.png", avg_rating: 9 }],
        },
      ],
    });
    expect(root.textContent).toContain("30");
    expect(root.querySelector("img")?.src).toContain("best.png");
    view.append({
      items: [
        {
          parameter: "steps",
          value: "40",
          sample_count: 2,
          best_images: [],
        },
      ],
    });
    expect(
      root
        .querySelector('[data-analytics-parameter="steps"]')
        ?.getAttribute("aria-pressed"),
    ).toBe("true");

    view.render("parameters", {
      view: "values",
      parameter: "seed",
      items: [],
    });
    expect(root.textContent).toContain("Keine Werte");

    view.render("parameters", { view: "summary", items: [] });
    expect(root.textContent).toContain("Keine rechnerischen Empfehlungen");
    expect(root.textContent).toContain("Keine beobachteten Setups");
    view.append({ items: [setup()] });
  });

  it("renders prompt combinations, render setups, and focused details", () => {
    const { root, view } = fixture();
    view.render("combinations", {
      view: "prompt",
      items: [
        {
          composition_uid: "composition-a",
          component_names: ["Aiko", "Rooftop"],
          image_count: 2,
          rating_count: 3,
          average_rating: 7.5,
          best_images: [],
        },
        {
          composition_uid: "composition-b",
          component_names: null,
          image_count: 1,
          rating_count: 1,
          average_rating: null,
          best_images: [{ url: "combo.png", avg_rating: null }],
        },
      ],
    });

    expect(root.textContent).toContain("Aiko");
    expect(root.textContent).toContain("composition-b");
    expect(root.textContent).toContain("Technische Setups anzeigen");
    view.append({
      items: [
        {
          composition_uid: "composition-c",
          component_names: ["Kaori"],
        },
      ],
    });
    view.renderCompositionSetups("composition-a", { rows: [setup()] });
    expect(root.textContent).toContain("Beobachtete Render-Setups");
    view.renderCompositionSetups("composition-a", { rows: [] });
    expect(root.textContent).toContain("Keine technischen Setups");
    view.renderCompositionSetups("missing", { rows: [] });

    view.render("combinations", { view: "render", items: [setup()] });
    expect(root.textContent).toContain("model.safetensors");
    expect(
      root
        .querySelector('[data-analytics-view="render"]')
        ?.getAttribute("aria-pressed"),
    ).toBe("true");

    view.render("combinations", { items: [] });
    expect(root.textContent).toContain("Keine Kombinationen");
    view.clear();
    expect(root.children).toHaveLength(0);
    view.dispose();
  });
});

function fixture(actions = {}) {
  const root = document.createElement("div");
  return { root, view: new AnalyticsView(root, actions) };
}

function setup() {
  return {
    setup_key: "setup-a",
    checkpoint: "model.safetensors",
    stages: [
      {
        role: "base",
        sampler: "euler",
        scheduler: "normal",
        steps: 30,
        cfg: 6.5,
        denoise: 1,
      },
    ],
    image_count: 2,
    rating_count: 3,
    average_rating: 8.5,
    lower_bound: 0.6,
    best_images: [],
  };
}
