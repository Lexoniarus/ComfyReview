import { beforeEach, describe, expect, it, vi } from "vitest";

import { CardWorkshopController } from "../../static/js/card-factory/workshop-controller.js";
import { CardWorkshopView } from "../../static/js/card-factory/workshop-view.js";

describe("Card workshop", () => {
  beforeEach(() => {
    document.body.innerHTML = workshopMarkup();
  });

  it("renders authoritative artifacts and delegates candidate acceptance", () => {
    const onAccept = vi.fn();
    const view = new CardWorkshopView(document.querySelector("main"), {
      onAccept,
    });
    view.render(snapshot());

    expect(document.querySelector("[data-card-title]").textContent).toBe(
      "Neonwache",
    );
    expect(document.querySelector("[data-card-attack]").textContent).toBe(
      "100",
    );
    expect(document.querySelector("[data-card-traits]").textContent).toContain(
      "Präzisionsimpuls",
    );
    expect(document.querySelectorAll(".card-candidate")).toHaveLength(4);
    document.querySelector(".card-candidate button").click();
    expect(onAccept).toHaveBeenCalledWith("candidate-0");
    view.setBusy(true);
    view.setBusy(false);
    view.showError("kaputt");
    expect(document.querySelector("[data-workshop-status]").textContent).toBe(
      "kaputt",
    );
    view.dispose();
  });

  it("renders the idle empty state and rejects incomplete shells", () => {
    const view = new CardWorkshopView(document.querySelector("main"), {
      onAccept: vi.fn(),
    });
    const idle = snapshot({ candidates: [] });
    idle.operation_state = "idle";
    view.render(idle);
    expect(document.querySelector(".card-empty-state")).toBeTruthy();
    expect(document.querySelector("[data-workshop-status]").textContent).toBe(
      "Session Revision 1",
    );

    document.querySelector("[data-card-image]").remove();
    expect(() => view.render(idle)).toThrow("Missing [data-card-image]");
    document.body.innerHTML = workshopMarkup();
    document.querySelector("[data-generate-candidates]").remove();
    expect(
      () =>
        new CardWorkshopView(document.querySelector("main"), {
          onAccept: vi.fn(),
        }),
    ).toThrow("Missing [data-generate-candidates]");
  });

  it("renders accepted candidates with the locked acceptance label", () => {
    const view = new CardWorkshopView(document.querySelector("main"), {
      onAccept: vi.fn(),
    });
    const accepted = snapshot();
    accepted.candidates[0].status = "accepted";
    accepted.candidates[0].can_accept = false;
    view.render(accepted);
    expect(document.querySelector(".card-candidate button").textContent).toBe(
      "Angenommen",
    );

    const active = snapshot({ status: "submitted" });
    view.render(active);
    expect(document.querySelector("[data-workshop-status]").textContent).toBe(
      "4 Kandidaten werden verarbeitet",
    );
  });

  it("rejects a workshop shell without its required status element", () => {
    document.querySelector("[data-workshop-status]").remove();
    expect(
      () =>
        new CardWorkshopView(document.querySelector("main"), {
          onAccept: vi.fn(),
        }),
    ).toThrow("Missing [data-workshop-status]");
  });

  it("loads, polls, generates, accepts, develops and disposes", async () => {
    const api = {
      session: vi.fn(() => Promise.resolve(snapshot({ status: "submitted" }))),
      generate: vi.fn(() => Promise.resolve(snapshot({ revision: 2 }))),
      accept: vi.fn(() => Promise.resolve(snapshot({ revision: 3 }))),
      develop: vi.fn(() =>
        Promise.resolve(snapshot({ revision: 4, candidates: [] })),
      ),
    };
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const requests = requestFixture();
    const documentRef = new EventTarget();
    documentRef.visibilityState = "visible";
    const controller = new CardWorkshopController({
      sessionId: "session-1",
      api,
      view,
      requests,
      documentRef,
      pollInterval: 1,
    });
    await controller.start();
    expect(requests.schedule).toHaveBeenCalled();
    requests.schedule.mock.calls[0][0]();
    await settle();
    await controller.generate();
    await controller.accept("candidate-0");
    await controller.develop();
    documentRef.visibilityState = "hidden";
    documentRef.dispatchEvent(new Event("visibilitychange"));
    documentRef.visibilityState = "visible";
    documentRef.dispatchEvent(new Event("visibilitychange"));
    await settle();
    controller.dispose();
    expect(api.generate).toHaveBeenCalledWith(
      "session-1",
      1,
      expect.any(Object),
    );
    expect(api.accept).toHaveBeenCalledWith(
      "session-1",
      "candidate-0",
      2,
      expect.any(Object),
    );
    expect(api.develop).toHaveBeenCalledWith(
      "session-1",
      3,
      expect.any(Object),
    );
    expect(view.dispose).toHaveBeenCalledOnce();
    expect(requests.dispose).toHaveBeenCalledOnce();
  });

  it("surfaces operation failures and refreshes current state", async () => {
    const api = {
      session: vi.fn(() => Promise.resolve(snapshot())),
      generate: vi.fn(() => Promise.reject(new Error("generation kaputt"))),
      accept: vi.fn(() => Promise.reject(new Error("accept kaputt"))),
      develop: vi.fn(() => Promise.reject("develop kaputt")),
    };
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new CardWorkshopController({
      sessionId: "session-1",
      api,
      view,
      requests: requestFixture(),
    });
    await controller.start();
    await controller.generate();
    await controller.accept("candidate-0");
    await controller.develop();
    expect(view.showError).toHaveBeenCalledWith("generation kaputt");
    expect(view.showError).toHaveBeenCalledWith("accept kaputt");
    expect(view.showError).toHaveBeenCalledWith(
      "Die Anfrage ist fehlgeschlagen.",
    );
  });

  it("surfaces initial load failures and rejects incomplete controls", async () => {
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new CardWorkshopController({
      sessionId: "session-1",
      api: { session: vi.fn(() => Promise.reject(new Error("load kaputt"))) },
      view,
      requests: requestFixture(),
    });
    await controller.start();
    expect(view.showError).toHaveBeenCalledWith("load kaputt");

    document.querySelector("[data-develop-card]").remove();
    const incomplete = new CardWorkshopController({
      sessionId: "session-1",
      api: {},
      view,
      requests: requestFixture(),
    });
    await expect(incomplete.start()).rejects.toThrow(
      "Missing [data-develop-card]",
    );
  });

  it("keeps commands inert before the initial session and binds both controls", async () => {
    const api = {
      session: vi.fn(() => Promise.resolve(snapshot({ candidates: [] }))),
      generate: vi.fn(() => Promise.resolve(snapshot({ revision: 2 }))),
      accept: vi.fn(),
      develop: vi.fn(() => Promise.resolve(snapshot({ revision: 3 }))),
    };
    const view = {
      root: document.querySelector("main"),
      render: vi.fn(),
      setBusy: vi.fn(),
      showError: vi.fn(),
      dispose: vi.fn(),
    };
    const controller = new CardWorkshopController({
      sessionId: "session-1",
      api,
      view,
      requests: requestFixture(),
    });
    await controller.generate();
    await controller.accept("candidate-0");
    await controller.develop();
    expect(api.generate).not.toHaveBeenCalled();

    await controller.start();
    document.querySelector("[data-generate-candidates]").click();
    await settle();
    document.querySelector("[data-develop-card]").click();
    await settle();
    expect(api.generate).toHaveBeenCalledOnce();
    expect(api.develop).toHaveBeenCalledOnce();
  });
});

function snapshot(options = {}) {
  const status = options.status || "completed";
  const candidates =
    options.candidates ||
    Array.from({ length: 4 }, (_, slot) => ({
      candidate_id: `candidate-${slot}`,
      slot_index: slot,
      status,
      can_accept: status === "completed",
      image_url: slot === 0 ? "/candidate.png" : "",
      failure_category: slot === 3 ? "provider_failed" : null,
    }));
  return {
    session_id: "session-1",
    revision: options.revision || 1,
    operation_state: status === "completed" ? "generating" : "generating",
    active_reference: {
      image_uid: "image-1",
      image_url: "/image.png",
      kind: "source",
      visual_tier: 0,
    },
    semantic_profile: {
      summary: "Eine ruhige Figur bei Nacht.",
      subjects: ["person"],
      actions: ["observing"],
      mood: ["calm"],
      environment: ["urban"],
      objects: ["light"],
      signals: [{ concept_key: "focused", strength_milli: 900 }],
    },
    imprint: {
      world_style: "near_future",
      card_class: "striker",
      combat_role: "control",
      trait_lineage: "precision",
    },
    card_spec: {
      rarity_key: "common",
      level: 1,
      stats: { attack: 100, defense: 200, stat_profile_key: "balanced" },
      traits: [
        {
          mechanic: { key: "marked_strike" },
          canonical_rule_text: "Markiere ein Ziel.",
        },
      ],
    },
    visual_recipe: {
      positive_atoms: [
        { canonical_text: "neon focus", weight_milli: 1100, required: true },
      ],
      negative_atoms: [
        { canonical_text: "blur", weight_milli: 1000, required: false },
      ],
      diagnostics: [{ code: "merged", message: "Atom wurde zusammengeführt." }],
    },
    presentation: {
      card_title: "Neonwache",
      short_description: "Eine aufmerksame Kämpferin.",
      trait_display_names: ["Präzisionsimpuls"],
      flavor_text: "Sie wartet auf den richtigen Moment.",
    },
    actions: { can_generate: false, can_develop: false },
    candidates,
  };
}

function workshopMarkup() {
  return `<main data-card-workshop>
    <h1 data-card-title></h1><p data-card-summary></p><span data-workshop-status></span>
    <button data-generate-candidates></button><button data-develop-card></button>
    <h2 id="card-heading"></h2><img data-active-image><img data-card-image>
    <dl data-source-facts></dl><div data-semantic-profile></div>
    <span data-card-rarity></span><strong data-preview-title></strong>
    <strong data-card-attack></strong><strong data-card-defense></strong>
    <div data-card-traits></div><p data-card-flavor></p><dl data-card-imprint></dl>
    <div data-positive-atoms></div><div data-negative-atoms></div>
    <div data-recipe-diagnostics></div><div data-card-candidates></div>
  </main>`;
}

function requestFixture() {
  return {
    run: vi.fn((operation) => operation(new AbortController().signal)),
    schedule: vi.fn(() => 7),
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
