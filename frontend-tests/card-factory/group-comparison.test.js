import { beforeEach, describe, expect, it, vi } from "vitest";

import { CardCandidateGroupComparisonController } from "../../static/js/card-factory/group-comparison-controller.js";
import { CardCandidateGroupComparisonView } from "../../static/js/card-factory/group-comparison-view.js";

describe("Card Candidate comparison", () => {
  beforeEach(() => {
    document.body.innerHTML = markup();
  });

  it("renders four complete Cards and delegates only allowed acceptance", () => {
    const onAccept = vi.fn();
    const view = new CardCandidateGroupComparisonView(
      document.querySelector("main"),
      { onAccept },
    );

    view.render(group());

    expect(document.querySelectorAll(".complete-card-candidate")).toHaveLength(
      4,
    );
    expect(
      document.querySelector(".complete-card-candidate h2").textContent,
    ).toBe("Neonwache 1");
    expect(document.querySelector(".complete-card-body").textContent).toContain(
      "ATK 100",
    );
    expect(document.querySelector(".card-trait").textContent).toContain(
      "Markiere ein Ziel.",
    );
    document.querySelector(".complete-card-candidate button").click();
    expect(onAccept).toHaveBeenCalledWith("candidate-0");
  });

  it("polls active groups and routes accept, reject and retry mutations", async () => {
    const active = group({ status: "generating" });
    const ready = group();
    const api = {
      group: vi.fn().mockResolvedValueOnce(active).mockResolvedValue(ready),
      acceptCandidate: vi.fn(() => Promise.resolve({ card_id: "card-1" })),
      rejectGroup: vi.fn(() => Promise.resolve(group({ status: "rejected" }))),
      retryGroup: vi.fn(() => Promise.resolve({ group_id: "group-2" })),
    };
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const requests = requestFixture();
    const locationRef = { assign: vi.fn() };
    const controller = new CardCandidateGroupComparisonController({
      groupId: "group-1",
      api,
      view,
      requests,
      locationRef,
      pollInterval: 1,
    });

    await controller.start();
    expect(requests.schedule).toHaveBeenCalledOnce();
    requests.schedule.mock.calls[0][0]();
    await settle();
    await controller.accept("candidate-0");
    expect(locationRef.assign).toHaveBeenCalledWith("/card-deck");
    await controller.reject();
    await controller.retry();
    expect(api.rejectGroup).toHaveBeenCalledWith(
      "group-1",
      ready.revision,
      expect.any(Object),
    );
    expect(locationRef.assign).toHaveBeenCalledWith(
      "/card-candidate-groups/group-2",
    );
    controller.dispose();
    expect(view.dispose).toHaveBeenCalledOnce();
    expect(requests.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces request failures without calculating fallback state", async () => {
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new CardCandidateGroupComparisonController({
      groupId: "group-1",
      api: { group: vi.fn(() => Promise.reject(new Error("offline"))) },
      view,
      requests: requestFixture(),
    });

    await controller.start();

    expect(view.showError).toHaveBeenCalledWith("offline");
  });
});

function group(options = {}) {
  const status = options.status || "ready";
  return {
    group_id: "group-1",
    revision: 7,
    kind: "initial",
    status,
    source: { image_url: "/source.png" },
    reference: { image_url: "/source.png" },
    semantic_profile: {
      summary: "Eine konzentrierte Figur.",
      subjects: ["person"],
      actions: ["observing"],
      mood: ["calm"],
      environment: ["urban"],
    },
    imprint: {
      world_style: "near_future",
      card_class: "striker",
      combat_role: "control",
      trait_lineage: "precision",
    },
    actions: {
      can_accept: status === "ready",
      can_reject: status === "ready",
      can_retry: status === "ready",
    },
    candidates: Array.from({ length: 4 }, (_, slot) => ({
      candidate_id: `candidate-${slot}`,
      slot_index: slot,
      status: status === "ready" ? "completed" : "submitted",
      can_accept: status === "ready",
      image_url: `/candidate-${slot}.png`,
      failure_category: null,
      artifacts: {
        card: {
          rarity_key: "common",
          level: 1,
          stats: { attack: 100 + slot, defense: 200 - slot },
          traits: [
            {
              mechanic: { key: "marked_strike" },
              canonical_rule_text: "Markiere ein Ziel.",
            },
          ],
        },
        presentation: {
          presentation: {
            card_title: `Neonwache ${slot + 1}`,
            short_description: "Wartet auf den richtigen Moment.",
            trait_display_names: ["Präzisionsimpuls"],
          },
        },
        visual_recipe: { diagnostics: [] },
      },
    })),
  };
}

function markup() {
  return `<main data-card-candidate-group>
    <h1 data-comparison-title></h1><p data-comparison-summary></p>
    <span data-comparison-status></span><button data-reject-group></button>
    <button data-retry-group></button><img data-comparison-source>
    <dl data-comparison-facts></dl><div data-comparison-semantic></div>
    <dl data-comparison-imprint></dl><section data-comparison-candidates></section>
  </main>`;
}

function requestFixture() {
  return {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    schedule: vi.fn(() => 9),
    cancel: vi.fn(),
    cancelRequests: vi.fn(),
    dispose: vi.fn(),
  };
}

async function settle() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}
