import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequestLifecycle } from "../../static/js/core/request-lifecycle.js";
import { PlaygroundWorkspace } from "../../static/js/playground/playground-workspace.js";
import { VariantBoard } from "../../static/js/playground/variant-board.js";
import {
  VariantInspector,
  variantGenerationPayload,
  variantWithReviewedPayload,
} from "../../static/js/playground/variant-inspector.js";
import { VariantSession } from "../../static/js/playground/variant-session.js";

describe("Playground variant workspace", () => {
  beforeEach(() => document.body.replaceChildren());

  it("owns variant selection, stale state, review payloads and request transitions", async () => {
    const onChange = vi.fn();
    const session = new VariantSession(new RequestLifecycle(), onChange);
    expect(session.hasVariants).toBe(false);
    expect(session.canSubmit).toBe(false);
    expect(session.inspect("missing")).toBe(false);
    expect(session.select("missing", true)).toBe(false);
    expect(session.review("missing", {})).toBe(false);
    expect(session.reviewedPayload("missing")).toBeNull();
    session.markStale();

    await session.prepare(async () =>
      batch([variant("draft-1"), variant("draft-2", 2)]),
    );
    expect(session.hasVariants).toBe(true);
    expect(session.canSubmit).toBe(true);
    expect(session.activeVariant().draft_uid).toBe("draft-1");
    expect(session.selectedVariants()).toHaveLength(2);
    expect(session.inspect("draft-2")).toBe(true);
    expect(session.select("draft-1", false)).toBe(true);
    expect(session.select("draft-1", true)).toBe(true);
    expect(session.select("draft-1", false)).toBe(true);
    expect(session.selectedVariants().map((item) => item.draft_uid)).toEqual([
      "draft-2",
    ]);
    expect(session.review("draft-2", { draft_uid: "draft-2" })).toBe(true);
    expect(session.reviewedPayload("draft-2")).toEqual({
      draft_uid: "draft-2",
    });

    await expect(session.submit(async () => ({ ok: true }))).resolves.toEqual({
      ok: true,
    });
    await expect(
      session.submit(async () => Promise.reject(new Error("submit failed"))),
    ).rejects.toThrow("submit failed");
    session.markStale();
    expect(session.snapshot().stale).toBe(true);
    expect(session.canSubmit).toBe(false);
    await expect(session.submit(async () => ({}))).rejects.toThrow(
      "nicht generierbar",
    );

    await expect(
      session.prepare(async () => Promise.reject(new Error("prepare failed"))),
    ).rejects.toThrow("prepare failed");
    expect(session.hasVariants).toBe(true);
    expect(onChange).toHaveBeenCalled();
    session.dispose();
    expect(session.hasVariants).toBe(false);
  });

  it("rejects invalid or superseded batches without losing a visible batch", async () => {
    const session = new VariantSession(new RequestLifecycle());
    for (const invalid of [
      {},
      batch([{ draft_uid: "" }]),
      batch([variant("duplicate"), variant("duplicate")]),
    ]) {
      await expect(session.prepare(async () => invalid)).rejects.toThrow(
        "keinen gültigen Varianten-Batch",
      );
    }

    await session.prepare(async () => batch([variant("visible")]));
    let resolvePrepare;
    const pendingPrepare = session.prepare(
      () =>
        new Promise((resolve) => {
          resolvePrepare = resolve;
        }),
    );
    session.markStale();
    resolvePrepare(batch([variant("late")]));
    await expect(pendingPrepare).rejects.toMatchObject({ name: "AbortError" });
    expect(session.activeVariant().draft_uid).toBe("visible");

    await session.prepare(async () => batch([variant("submit-visible")]));
    let resolveSubmit;
    const pendingSubmit = session.submit(
      () =>
        new Promise((resolve) => {
          resolveSubmit = resolve;
        }),
    );
    session.markStale();
    resolveSubmit({ ok: true });
    await expect(pendingSubmit).rejects.toMatchObject({ name: "AbortError" });
    session.dispose();
  });

  it("renders selectable stale cards and forwards card actions", () => {
    const root = document.createElement("div");
    const onSelect = vi.fn();
    const onInspect = vi.fn();
    const board = new VariantBoard(root, { onSelect, onInspect });
    board.render({
      variants: [],
      selectedDraftUids: new Set(),
      activeDraftUid: "",
      stale: false,
      metadata: {},
    });
    expect(root.textContent).toContain("Noch keine Varianten");

    board.render({
      variants: [variant("draft-card")],
      selectedDraftUids: new Set(["draft-card"]),
      activeDraftUid: "draft-card",
      stale: true,
      metadata: { notice: "Auswahlraum ausgeschöpft" },
    });
    expect(root.textContent).toContain("Setup wurde geändert");
    expect(root.textContent).toContain("Auswahlraum ausgeschöpft");
    expect(root.textContent).toContain("character: Aiko");
    expect(root.textContent).toContain("Seed 1 · 24 Steps · CFG 6.5");
    expect(root.querySelector(".variant-card").dataset.active).toBe("true");
    const checkbox = root.querySelector("input");
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change"));
    click(root, "Prüfen & bearbeiten");
    expect(onSelect).toHaveBeenCalledWith("draft-card", false);
    expect(onInspect).toHaveBeenCalledWith("draft-card");
    board.dispose();
    expect(root.childElementCount).toBe(0);

    const defaultRoot = document.createElement("div");
    const defaults = new VariantBoard(defaultRoot);
    defaults.render({
      variants: [variant("default-card")],
      selectedDraftUids: new Set(["default-card"]),
      activeDraftUid: "default-card",
      stale: false,
      metadata: {},
    });
    defaultRoot.querySelector("input").dispatchEvent(new Event("change"));
    click(defaultRoot, "Prüfen & bearbeiten");
    defaults.dispose();
  });

  it("keeps reviewed atom edits concrete and rehydrates them for inspection", () => {
    const root = document.createElement("div");
    const state = document.createElement("span");
    const onChange = vi.fn();
    const inspector = new VariantInspector(root, state, onChange);
    expect(inspector.generationPayload()).toBeNull();
    const prepared = variant("draft-edit");
    inspector.render(prepared);
    expect(inspector.promptPayload()).toEqual(
      expect.objectContaining({ positive_atoms: expect.any(Array) }),
    );
    const input = root.querySelector("[data-atom-text]");
    input.value = "edited character";
    input.dispatchEvent(new Event("input"));
    const payload = inspector.generationPayload();
    expect(payload.draft_uid).toBe("draft-edit");
    expect(payload.prompt_groups[0].positive_atoms[0].text).toBe(
      "edited character",
    );
    expect(payload.sampler).toEqual(
      expect.objectContaining({ batch_runs: 1, randomize_seed: false }),
    );
    expect(onChange).toHaveBeenCalled();
    inspector.renderSnapshots({
      positive_prompt: "edited character",
      negative_prompt: "blur",
    });
    inspector.renderEvidence({ prompt_match: null, sampler_match: null });
    expect(root.textContent).toContain("edited character");

    const untouched = variantGenerationPayload(prepared);
    expect(untouched).toEqual(
      expect.objectContaining({
        draft_uid: "draft-edit",
        source_image_uid: null,
        checkpoint: "model.safetensors",
      }),
    );
    const rehydrated = variantWithReviewedPayload(prepared, payload);
    expect(rehydrated.groups[0].positive_atoms[0].text).toBe(
      "edited character",
    );
    inspector.clear();
    inspector.dispose();

    const defaultRoot = document.createElement("div");
    const defaults = new VariantInspector(
      defaultRoot,
      document.createElement("span"),
    );
    defaults.render(prepared);
    defaultRoot
      .querySelector("[data-atom-text]")
      .dispatchEvent(new Event("input"));
    defaults.renderEvidence({
      prompt_match: { image_uid: "image-a", image_url: "/image-a.png" },
      sampler_match: null,
    });
    defaultRoot.querySelector(".evidence-carousel-image").click();
    defaults.dispose();
  });

  it("owns Setup and Varianten navigation with one listener lifecycle", () => {
    const root = document.createElement("div");
    const setupButton = stepButton("setup");
    const variantsButton = stepButton("variants");
    const setup = panel("setup");
    const variants = panel("variants");
    const boardButton = viewButton("board");
    const inspectorButton = viewButton("inspector");
    const closeInspector = document.createElement("button");
    closeInspector.dataset.closeVariantInspector = "";
    root.append(
      setupButton,
      variantsButton,
      boardButton,
      inspectorButton,
      closeInspector,
      setup,
      variants,
    );
    const onChange = vi.fn();
    const workspace = new PlaygroundWorkspace(root, onChange);
    expect(setup.hidden).toBe(false);
    expect(variants.hidden).toBe(true);
    expect(workspace.show("variants")).toBe(false);
    workspace.setVariantsAvailable(true);
    variantsButton.click();
    expect(variants.hidden).toBe(false);
    expect(setup.hidden).toBe(true);
    expect(onChange).toHaveBeenCalled();
    inspectorButton.click();
    expect(root.dataset.variantView).toBe("inspector");
    expect(root.dataset.inspectorOpen).toBe("true");
    expect(inspectorButton.getAttribute("aria-selected")).toBe("true");
    closeInspector.click();
    expect(root.dataset.variantView).toBe("board");
    workspace.openInspector();
    expect(root.dataset.inspectorOpen).toBe("true");
    workspace.closeInspector(false);
    expect(root.dataset.inspectorOpen).toBe("false");
    workspace.setVariantsAvailable(false);
    expect(setup.hidden).toBe(false);
    expect(workspace.show("unknown")).toBe(true);
    workspace.dispose();

    const defaultWorkspace = new PlaygroundWorkspace(root);
    defaultWorkspace.setVariantsAvailable(true);
    defaultWorkspace.show("variants");
    defaultWorkspace.dispose();
  });
});

function variant(draftUid, seed = 1) {
  return {
    draft_uid: draftUid,
    seed,
    generation: {
      checkpoint: "model.safetensors",
      sampler: "euler",
      scheduler: "normal",
      seed,
      steps: 24,
      cfg: 6.5,
      denoise: 1,
      aspect_format: "1:1",
      resolution_class: "1080",
    },
    components: [
      {
        kind: "character",
        name: "Aiko",
        latest_revision: { revision_number: 2 },
      },
    ],
    prompt_selections: [
      {
        kind: "character",
        component_uid: "character-a",
        revision_uid: "revision-character-a",
      },
    ],
    prompt_groups: [
      {
        kind: "character",
        name: "Aiko",
        component_uid: "character-a",
        revision_uid: "revision-character-a",
        candidate_uid: null,
        positive_atoms: [{ text: "aiko", weight: 1 }],
        negative_atoms: [{ text: "blur", weight: 1 }],
      },
    ],
    groups: [
      {
        kind: "character",
        name: "Aiko",
        component_uid: "character-a",
        revision_uid: "revision-character-a",
        candidate_uid: null,
        positive_atoms: [{ text: "aiko", weight: 1 }],
        negative_atoms: [{ text: "blur", weight: 1 }],
      },
      {
        kind: "lora",
        name: "Style",
        component_uid: "lora-a",
        revision_uid: "revision-lora-a",
        positive_atoms: [],
        negative_atoms: [],
      },
    ],
    positive_atoms: [{ text: "aiko", weight: 1 }],
    negative_atoms: [{ text: "blur", weight: 1 }],
    positive_prompt: "aiko",
    negative_prompt: "blur",
    loras: [
      {
        lora_uid: "lora-a",
        revision_uid: "revision-lora-a",
        provider_name: "style.safetensors",
        model_strength: 0.8,
        clip_strength: 0.7,
      },
    ],
  };
}

function batch(variants) {
  return {
    requested_count: variants.length,
    unique_count: variants.length,
    repeated_count: 0,
    diversity_exhausted: false,
    notice: "",
    variants,
  };
}

function click(root, label) {
  [...root.querySelectorAll("button")]
    .find((button) => button.textContent === label)
    .click();
}

function stepButton(step) {
  const button = document.createElement("button");
  button.dataset.workspaceStep = step;
  return button;
}

function viewButton(view) {
  const button = document.createElement("button");
  button.dataset.variantView = view;
  return button;
}

function panel(step) {
  const element = document.createElement("section");
  element.dataset.workspacePanel = step;
  return element;
}
