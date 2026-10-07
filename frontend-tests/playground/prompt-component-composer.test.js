import { beforeEach, describe, expect, it, vi } from "vitest";

import { PromptComponentComposer } from "../../static/js/playground/prompt-component-composer.js";

describe("Prompt component composer", () => {
  beforeEach(() => document.body.replaceChildren());

  it("owns exact local overrides and restores the catalog atoms", () => {
    const root = document.createElement("div");
    const onChange = vi.fn();
    const onReset = vi.fn();
    const composer = new PromptComponentComposer(root, {
      kind: "character",
      componentUid: "character-a",
      revisionUid: "revision-a",
      candidateUid: "candidate-a",
      positiveAtoms: [{ text: "silver hair", weight: 1 }],
      negativeAtoms: [{ text: "blur", weight: 1.1 }],
      onChange,
      onReset,
    });
    document.body.append(root);

    expect(composer.isDirty()).toBe(false);
    const positive = root.querySelector("[data-atom-text]");
    positive.value = "cyan hair";
    positive.dispatchEvent(new Event("input"));
    const negative = root.querySelectorAll("[data-atom-text]")[1];
    negative.dispatchEvent(new Event("input"));
    expect(onChange).toHaveBeenCalledTimes(2);
    expect(composer.isDirty()).toBe(true);
    expect(composer.value()).toEqual({
      kind: "character",
      component_uid: "character-a",
      revision_uid: "revision-a",
      candidate_uid: "candidate-a",
      positive_atoms: [{ text: "cyan hair", weight: 1 }],
      negative_atoms: [{ text: "blur", weight: 1.1 }],
    });

    click(root, "Auf Katalogstand zurücksetzen");
    expect(onReset).toHaveBeenCalledTimes(1);
    expect(composer.isDirty()).toBe(false);
    expect(composer.value().candidate_uid).toBeNull();
    expect(root.textContent).toContain("Katalogstand wiederhergestellt");

    composer.setBusy(true);
    expect(
      [...root.querySelectorAll("input, button")].every(
        (item) => item.disabled,
      ),
    ).toBe(true);
    composer.setBusy(false);
    composer.dispose();
  });

  it("materializes a manual candidate and reports failures locally", async () => {
    const root = document.createElement("div");
    const onSaved = vi.fn();
    const onSave = vi.fn(async (payload) => ({
      candidate_uid: "candidate-saved",
      candidate_type: payload.candidate_type,
    }));
    const composer = new PromptComponentComposer(root, {
      kind: "scene",
      componentUid: "scene-a",
      revisionUid: "revision-scene-a",
      positiveAtoms: [{ text: "rooftop", weight: 1 }],
      onSave,
      onSaved,
    });

    const saved = await composer.save();
    expect(onSave).toHaveBeenCalledWith(
      {
        component_uid: "scene-a",
        source_revision_uid: "revision-scene-a",
        candidate_type: "manual",
        positive_atoms: [{ text: "rooftop", weight: 1 }],
        negative_atoms: [],
      },
      expect.any(AbortSignal),
    );
    expect(saved.candidate_uid).toBe("candidate-saved");
    expect(composer.value().candidate_uid).toBe("candidate-saved");
    expect(onSaved).toHaveBeenCalledWith(saved);
    expect(root.textContent).toContain("Als Katalog-Test gespeichert");
    composer.dispose();

    const failedRoot = document.createElement("div");
    const failed = new PromptComponentComposer(failedRoot, {
      kind: "scene",
      componentUid: "scene-a",
      revisionUid: "revision-scene-a",
      onSave: async () => Promise.reject(new Error("failed")),
    });
    expect(await failed.save()).toBeNull();
    expect(failedRoot.textContent).toContain(
      "Katalog-Test konnte nicht gespeichert werden",
    );
    failed.dispose();
  });

  it("cancels superseded requests and supports a read-only composer", async () => {
    const root = document.createElement("div");
    let firstSignal;
    let resolveSecond;
    const onSave = vi
      .fn()
      .mockImplementationOnce((_payload, signal) => {
        firstSignal = signal;
        return new Promise((_resolve, reject) => {
          signal.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        });
      })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve;
          }),
      );
    const composer = new PromptComponentComposer(root, {
      kind: "pose",
      componentUid: "pose-a",
      revisionUid: "revision-pose-a",
      onSave,
    });

    const first = composer.save();
    const second = composer.save();
    expect(firstSignal.aborted).toBe(true);
    resolveSecond({ candidate_uid: "candidate-pose" });
    await expect(first).resolves.toBeNull();
    await expect(second).resolves.toEqual({ candidate_uid: "candidate-pose" });
    composer.dispose();

    const readOnly = new PromptComponentComposer(
      document.createElement("div"),
      {
        kind: "lighting",
        componentUid: "lighting-a",
        revisionUid: "revision-lighting-a",
      },
    );
    expect(await readOnly.save()).toBeNull();
    readOnly.reset();
    readOnly.dispose();
  });
});

function click(root, label) {
  [...root.querySelectorAll("button")]
    .find((candidate) => candidate.textContent === label)
    .click();
}
