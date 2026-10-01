import { beforeEach, describe, expect, it, vi } from "vitest";

import { GenerationDetail } from "../../static/js/generations/generation-detail.js";
import {
  GenerationList,
  lifecycleLabel,
  shortUid,
} from "../../static/js/generations/generation-list.js";

describe("Generation lifecycle components", () => {
  beforeEach(() => document.body.replaceChildren());

  it("renders persisted lifecycle entries, filters and owns selection", () => {
    const root = document.createElement("div");
    const filter = document.createElement("select");
    filter.append(new Option("Alle", ""), new Option("Läuft", "running"));
    const onSelect = vi.fn();
    const onFilter = vi.fn();
    const list = new GenerationList(root, filter, { onSelect, onFilter });

    list.render([]);
    expect(root.textContent).toContain("Keine Generierungen");
    list.render([
      {
        generation_uid: "generation-with-a-very-long-stable-uid",
        status: "running",
        model: "anime",
        output_count: 2,
      },
      {
        generation_uid: "short-id",
        status: "custom",
        model: "",
        output_count: 0,
      },
    ]);
    root.querySelector("button").click();
    expect(onSelect).toHaveBeenCalledWith(
      "generation-with-a-very-long-stable-uid",
    );
    list.select("short-id");
    expect(
      root.querySelectorAll("button")[1].getAttribute("aria-current"),
    ).toBe("true");
    filter.value = "running";
    filter.dispatchEvent(new Event("change"));
    expect(list.status()).toBe("running");
    expect(onFilter).toHaveBeenCalledOnce();
    expect(lifecycleLabel("completed")).toBe("Abgeschlossen");
    expect(lifecycleLabel("custom")).toBe("custom");
    expect(lifecycleLabel("")).toBe("Unbekannt");
    expect(shortUid("short-id")).toBe("short-id");
    expect(shortUid("generation-with-a-very-long-stable-uid")).toContain("…");
    list.dispose();
    expect(root.children).toHaveLength(0);
  });

  it("renders safe detail, all outputs and reconciliation action", () => {
    const root = document.createElement("div");
    const onReconcile = vi.fn();
    const detail = new GenerationDetail(root, { onReconcile });
    const generation = generationDetail();

    detail.render(generation);
    expect(root.textContent).toContain("default-character · v1");
    expect(root.querySelectorAll("figure")).toHaveLength(2);
    expect(root.querySelector("img").getAttribute("src")).toBe(
      "/files/image-1.png",
    );
    root.querySelector("button").click();
    expect(onReconcile).toHaveBeenCalledWith("generation-1", "prompt-1");

    detail.render({
      ...generation,
      status: "completed",
      prompt_id: null,
      blueprint_uid: null,
      blueprint_version: null,
      graph_hash: null,
      checkpoint: "",
      positive_prompt: "",
      negative_prompt: "",
      outputs: [],
    });
    expect(root.textContent).toContain("Legacy / unbekannt");
    expect(root.textContent).toContain("Noch keine kanonischen Outputs");
    expect(root.querySelector("button")).toBeNull();
    detail.clear();
    expect(root.textContent).toContain("Wähle eine Generierung");
    detail.dispose();
    expect(root.children).toHaveLength(0);
  });
});

function generationDetail() {
  return {
    generation_uid: "generation-1",
    status: "reconciliation_required",
    prompt_id: "prompt-1",
    checkpoint: "model.safetensors",
    blueprint_uid: "default-character",
    blueprint_version: 1,
    graph_hash: "graph-hash",
    positive_prompt: "positive <script>alert(1)</script>",
    negative_prompt: "negative",
    outputs: [
      {
        image_uid: "image-1",
        role: "primary",
        node_id: "42",
        output_index: 0,
        image_url: "/files/image-1.png",
      },
      {
        image_uid: "image-2",
        role: "primary",
        node_id: "42",
        output_index: 1,
        image_url: "/files/image-2.png",
      },
    ],
  };
}
