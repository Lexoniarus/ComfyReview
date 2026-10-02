import { beforeEach, describe, expect, it } from "vitest";

import { AnalyticsView } from "../../static/js/analytics/analytics-view.js";

describe("AnalyticsView", () => {
  beforeEach(() => document.body.replaceChildren());

  it("renders evidence, worked calculations, and approximation candidates", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("overview", {
      t: 4,
      dw: 5,
      stable: [
        {
          checkpoint: "Aiko <script>",
          n: 4,
          avg_rating: 8.5,
          exp_success_rate: 0.75,
          stability_lb05: 0.6,
        },
        {},
      ],
      avoid: [],
      approx: {
        base: { n: 40, exp: 0.5 },
        notes: "Additive Schätzung",
        rows: [
          {
            sampler: "euler",
            scheduler: "normal",
            steps: 30,
            cfg: 6.5,
            pred_success: 0.8,
            support_min: 12,
          },
        ],
      },
    });

    expect(root.textContent).toContain("Aiko <script>");
    expect(root.querySelector("script")).toBeNull();
    expect(root.textContent).toContain("So wird die Evidenz gelesen");
    expect(root.textContent).toContain("Beispiel: 4 Beobachtungen");
    expect(root.textContent).toContain("euler · normal");
    expect(root.textContent).toContain("Keine Einträge");

    view.render("overview", { stable: [], avoid: [], approx: null });
    expect(root.textContent).toContain("Keine rechnerischen Kandidaten");
    view.clear();
    expect(root.children).toHaveLength(0);
  });

  it("renders canonical scope groups with archived state and image examples", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("scopes", {
      rows: [
        {
          kind: "character",
          component_uid: "character-a",
          name: "Aiko",
          archived: true,
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
          best_images: [
            { url: "image.png", avg_rating: 9 },
            { url: "", avg_rating: 8 },
          ],
        },
      ],
    });

    expect(root.textContent).toContain("Scope-Evidenz");
    expect(root.textContent).toContain("Charakter");
    expect(root.textContent).toContain("Aiko");
    expect(root.textContent).toContain("Archiviert");
    expect(root.textContent).toContain("2 Bilder · 4 Bewertungen");
    expect(root.querySelector("img")?.getAttribute("src")).toBe("image.png");
    expect(root.querySelector(".analytics-image-strip")?.dataset.count).toBe(
      "1",
    );
    expect(root.querySelector("script")).toBeNull();

    view.render("scopes", { rows: null });
    expect(root.textContent).toContain("Keine Scopes");
  });

  it("renders calculated best cases and observed parameter examples", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("parameters", {
      best: [
        {
          checkpoint: "model.safetensors",
          score: 0.7,
          checkpoint_stats: { stability_lb05: 0.6 },
          picks: {
            sampler: { value: "euler" },
            scheduler: { value: "normal" },
            steps: { value: 30 },
          },
        },
      ],
      best_tested: [
        {
          combo_key:
            "ckpt=model.safetensors|sampler=euler|sched=normal|steps=30|cfg=6.5|denoise=1",
          n: 12,
          avg_rating: 8.5,
          exp_success_rate: 0.7,
          stability_lb05: 0.6,
        },
      ],
      stats: [
        {
          key: "steps",
          title: "Steps",
          rows: [
            {
              value: 30,
              n: 5,
              avg_rating: 8,
              exp_success_rate: 0.7,
              stability_lb05: 0.6,
              best_images: [{ url: "best.png", avg_rating: 9 }],
            },
          ],
        },
        {
          key: "cfg",
          title: "CFG",
          rows: [{ value: 6.5, n: 8, avg_rating: 7.5 }],
        },
        { key: "sampler", title: "Sampler", rows: [] },
      ],
    });

    expect(root.textContent).toContain("Best Case · berechnet");
    expect(root.textContent).toContain("Sampler euler");
    expect(root.textContent).toContain("Steps 30");
    expect(root.querySelector("img")?.getAttribute("src")).toBe("best.png");
    expect(root.textContent).toContain("Getestet");
    expect(root.textContent).toContain("Keine Werte für diesen Parameter");
    root.querySelectorAll('[role="tab"]')[1].click();
    expect(root.textContent).toContain("euler · normal · 30 Steps · CFG 6.5");
    root.querySelectorAll('[role="tab"]')[3].click();
    expect(root.querySelectorAll('[role="tabpanel"]')[3].hidden).toBe(false);

    view.render("parameters", { stats: [], best: [], best_tested: [] });
    expect(root.textContent).toContain("Keine berechneten Vorschläge");
    expect(root.textContent).toContain("Keine ausreichend belegten");
    expect(root.textContent).toContain("Keine Parameterdaten");
  });

  it("renders observed composition cards and explicit empty states", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("combinations", {
      rows: [
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
    expect(root.textContent).toContain("Rooftop");
    expect(root.textContent).toContain("composition-b");
    expect(root.textContent).toContain("1 Bild · 1 Bewertung");
    expect(root.textContent).toContain("Kein Bildbeispiel");
    expect(root.querySelector("img")?.getAttribute("src")).toBe("combo.png");

    view.render("combinations", { rows: [] });
    expect(root.textContent).toContain("Keine Kombinationen");
  });
});
