import { beforeEach, describe, expect, it } from "vitest";

import { AnalyticsView } from "../../static/js/analytics/analytics-view.js";

describe("AnalyticsView", () => {
  beforeEach(() => document.body.replaceChildren());

  it("renders overview recommendations and safe empty groups", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("overview", {
      stable: [{ label: "Aiko <script>", n: 4, avg_rating: 8.5 }, {}],
      avoid: [],
    });

    expect(root.textContent).toContain("Aiko <script>");
    expect(root.querySelector("script")).toBeNull();
    expect(root.textContent).toContain("Keine Einträge");
    view.clear();
    expect(root.children).toHaveLength(0);
  });

  it("renders scope and combination reports from server values", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("scopes", {
      rows: [
        {
          kind: "character",
          component_uid: "character-a",
          name: "Aiko",
          image_count: 2,
          rating_count: 4,
          average_rating: 8.5,
        },
      ],
    });
    expect(root.textContent).toContain("Charakter");
    expect(root.textContent).toContain("Aiko");
    expect(root.textContent).toContain("8,5");

    view.render("combinations", {
      rows: [
        {
          composition_uid: "composition-a",
          component_names: ["Aiko", "Rooftop"],
          image_count: 2,
          rating_count: 3,
          average_rating: 7.5,
        },
      ],
    });
    expect(root.textContent).toContain("Aiko · Rooftop");
    expect(root.textContent).toContain("7,5");
  });

  it("renders parameter sections and explicit empty states", () => {
    const root = document.createElement("div");
    const view = new AnalyticsView(root);

    view.render("parameters", { stats: [] });
    expect(root.textContent).toContain("Keine Parameterdaten");

    view.render("parameters", {
      stats: [
        {
          key: "steps",
          title: "Steps",
          rows: [
            {
              value: 24,
              sample_count: 5,
              mean_score: 8,
              lb05: 6.5,
            },
          ],
        },
      ],
    });
    expect(root.textContent).toContain("Steps");
    expect(root.textContent).toContain("24");

    view.render("scopes", { rows: null });
    expect(root.textContent).toContain("Keine Daten");
  });
});
