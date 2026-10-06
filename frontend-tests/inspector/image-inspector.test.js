import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImageInspector } from "../../static/js/inspector/image-inspector.js";

describe("ImageInspector", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("composes complete canonical context without owning mutations", () => {
    const root = document.createElement("aside");
    document.body.append(root);
    const onCuration = vi.fn();
    const onContentLevel = vi.fn();
    const onDelete = vi.fn();
    const onClose = vi.fn();
    const inspector = new ImageInspector(root, {
      onCuration,
      onContentLevel,
      onDelete,
      onClose,
    });

    inspector.setCurationBusy(true);
    inspector.showCurationError("Vorheriger Fehler");
    inspector.setCurationOptions(["character_face", "outfit", "custom_set"]);
    inspector.render({
      image_uid: "image-1",
      generation_uid: "generation-1",
      image_url: "/files/image.png",
      classification: "unclassified",
      review_summary: { average_rating: 9, rating_count: 2 },
      scopes: [{ kind: "outfit", name: "Sommerkleid" }],
      prompt_snapshot: {
        positive: "portrait",
        negative: "blur",
        draft_overridden: true,
      },
      generation_settings: {
        model: "SDXL",
        checkpoint: "model.safetensors",
        seed: 42,
        steps: 30,
        cfg: 6.5,
        sampler: "euler",
        scheduler: "normal",
        denoise: 1,
      },
      workflow_provenance: {
        blueprint_uid: "default-character",
        blueprint_version: 1,
        graph_hash: "abc123",
      },
      output_role: "primary",
      output_index: 0,
      curation: { set_key: "outfit" },
      content_classification: {
        inferred_level: "sexy",
        effective_level: "lewd",
        override_level: "lewd",
      },
    });
    inspector.setCurationOptions(["character_face", "outfit", "custom_set"]);

    expect(root.textContent).toContain("Unklassifiziert");
    expect(root.textContent).toContain("Ø 9,0 / 10 · 2×");
    expect(root.textContent).toContain("Draft-Override");
    expect(root.textContent).toContain("model.safetensors");
    expect(root.textContent).toContain("primary · Index 0");
    expect(root.textContent).toContain("default-character · v1");
    expect(root.querySelector("img")?.src).toContain("/files/image.png");
    expect(root.textContent).toContain("Vorheriger Fehler");
    expect(root.textContent).toContain("Automatisch: Sexy");
    root.querySelector(".inspector-close")?.click();
    expect(onClose).toHaveBeenCalledOnce();

    inspector.setContentLevelBusy(true);
    inspector.showContentLevelError("Einstufung fehlgeschlagen");
    expect(root.textContent).toContain("Einstufung fehlgeschlagen");
    inspector.setContentLevelBusy(false);
    root.querySelector("[data-content-action='assign']")?.click();
    expect(onContentLevel).toHaveBeenCalledWith("image-1", "lewd");
    root.querySelector("[data-content-action='delete']")?.click();
    expect(onDelete).toHaveBeenCalledWith("image-1");

    inspector.setCurationBusy(false);
    const select = root.querySelector("[data-curation-set]");
    expect(select).toBeInstanceOf(HTMLSelectElement);
    expect(select.value).toBe("outfit");
    select.value = "character_face";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    root.querySelector("[data-curation-assign]")?.click();
    expect(onCuration).toHaveBeenCalledWith("image-1", "character_face");

    inspector.renderReviews([
      {
        event_type: "rating",
        rating: 9,
        reviewed_at: "2026-01-02 12:30:00",
      },
      { event_type: "delete", reviewed_at: "invalid" },
      { event_type: "restore", reviewed_at: "" },
      { event_type: "custom", reviewed_at: "2026-01-01T10:00:00" },
    ]);
    expect(root.textContent).toContain("Bewertung 9 / 10");
    expect(root.textContent).toContain("Gelöscht");
    expect(root.textContent).toContain("Wiederhergestellt");
    expect(root.textContent).toContain("custom");
    expect(root.textContent).toContain("Zeitpunkt unbekannt");

    inspector.reviewsLoading();
    expect(root.textContent).toContain("Bewertungshistorie wird geladen");
    inspector.reviewsError("");
    expect(root.textContent).toContain("konnte nicht geladen");
    inspector.showCurationError("");
    expect(root.querySelector("[data-curation-status]")?.hidden).toBe(true);
    inspector.dispose();
    root.querySelector(".inspector-close")?.click();
    expect(onClose).toHaveBeenCalledOnce();
    root.querySelector("[data-curation-assign]")?.click();
    expect(onCuration).toHaveBeenCalledOnce();
  });

  it("renders empty legacy-safe values and inspector states", () => {
    const root = document.createElement("aside");
    const inspector = new ImageInspector(root);

    inspector.empty();
    expect(root.textContent).toContain("Wähle");
    inspector.loading();
    expect(root.textContent).toContain("geladen");
    inspector.error("");
    expect(root.textContent).toContain("konnten nicht");

    inspector.setCurationOptions(["custom_set"]);
    inspector.render({ image_uid: "image-2" });
    expect(root.textContent).toContain("Klassifiziert");
    expect(root.textContent).toContain("Noch unbewertet");
    expect(root.textContent).toContain("Keine kanonischen Scopes");
    expect(root.textContent).toContain("Legacy / unbekannt");
    expect(root.textContent).toContain("unbekannt · Index ?");
    expect(root.textContent).toContain("custom set");

    inspector.renderReviews([]);
    expect(root.textContent).toContain("Noch keine Review-Events");
    inspector.reviewsError("Historie fehlgeschlagen");
    expect(root.textContent).toContain("Historie fehlgeschlagen");

    const select = root.querySelector("[data-curation-set]");
    select.value = "custom_set";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    root
      .querySelector("[data-curation-assign]")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    select.value = "";
    root
      .querySelector("[data-curation-assign]")
      ?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const curation = root.querySelector(".inspector-curation");
    curation?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    const textTarget = document.createTextNode("text");
    curation?.append(textTarget);
    textTarget.dispatchEvent(new Event("click", { bubbles: true }));
    inspector.dispose();
  });
});
