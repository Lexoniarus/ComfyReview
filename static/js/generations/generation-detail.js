import { lifecycleLabel } from "./generation-list.js";

/** Render one canonical generation detail and own its reconciliation action. */
export class GenerationDetail {
  /** @param {HTMLElement} root @param {{onReconcile: (uid: string, promptId: string | null) => void, createGeneratorActions?: (uid: string) => HTMLElement}} actions */
  constructor(root, actions) {
    this.root = root;
    this.actions = actions;
    this.abortController = new AbortController();
  }

  /** @param {Record<string, any>} generation */
  render(generation) {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    const heading = document.createElement("div");
    heading.className = "generation-detail-heading";
    const title = document.createElement("h2");
    title.textContent = "Generierungsdetails";
    const badge = document.createElement("span");
    badge.className = "generation-status-badge";
    badge.dataset.status = String(generation.status);
    badge.textContent = lifecycleLabel(String(generation.status));
    heading.append(title, badge);

    const facts = document.createElement("dl");
    facts.className = "generation-facts";
    appendFact(facts, "Generation UID", generation.generation_uid);
    appendFact(facts, "ComfyUI Prompt ID", generation.prompt_id || "—");
    appendFact(facts, "Checkpoint", generation.checkpoint || "—");
    appendFact(
      facts,
      "Blueprint",
      generation.blueprint_uid
        ? `${generation.blueprint_uid} · v${generation.blueprint_version ?? "?"}`
        : "Legacy / unbekannt",
    );
    appendFact(facts, "Graph-Hash", generation.graph_hash || "—");
    if (generation.failure_reason) {
      appendFact(facts, "Abgleichhinweis", generation.failure_reason);
    }

    const prompts = document.createElement("section");
    prompts.className = "generation-prompt-grid";
    prompts.append(
      promptBlock("Positiver Snapshot", generation.positive_prompt),
      promptBlock("Negativer Snapshot", generation.negative_prompt),
    );

    const outputs = document.createElement("section");
    outputs.className = "generation-outputs";
    const outputTitle = document.createElement("h3");
    outputTitle.textContent = `Outputs · ${(generation.outputs || []).length}`;
    outputs.append(outputTitle);
    const grid = document.createElement("div");
    grid.className = "generation-output-grid";
    for (const output of generation.outputs || []) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      image.src = String(output.image_url || "");
      image.alt = `${output.role || "Output"} ${Number(output.output_index) + 1}`;
      image.loading = "lazy";
      const caption = document.createElement("figcaption");
      caption.textContent = `${output.role} · Node ${output.node_id} · Index ${output.output_index}`;
      figure.append(image, caption);
      if (output.image_uid && this.actions.createGeneratorActions) {
        figure.append(
          this.actions.createGeneratorActions(String(output.image_uid)),
        );
      }
      grid.append(figure);
    }
    if (!grid.children.length) {
      const empty = document.createElement("p");
      empty.className = "generation-empty";
      empty.textContent = "Noch keine kanonischen Outputs vorhanden.";
      grid.append(empty);
    }
    outputs.append(grid);
    this.root.append(heading, facts, prompts, outputs);

    if (generation.status === "reconciliation_required") {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "primary-button";
      button.textContent = "Auftrag / Output abgleichen";
      button.addEventListener(
        "click",
        () =>
          this.actions.onReconcile(
            String(generation.generation_uid),
            generation.prompt_id ? String(generation.prompt_id) : null,
          ),
        { signal: this.abortController.signal },
      );
      this.root.append(button);
    }
  }

  /** Show the neutral unselected state. */
  clear() {
    this.abortController.abort();
    this.abortController = new AbortController();
    this.root.replaceChildren();
    const message = document.createElement("p");
    message.className = "generation-empty";
    message.textContent =
      "Wähle eine Generierung für alle Details und Outputs.";
    this.root.append(message);
  }

  /** Release owned reconciliation listeners. */
  dispose() {
    this.abortController.abort();
    this.root.replaceChildren();
  }
}

/** @param {HTMLDListElement} root @param {string} label @param {unknown} value */
function appendFact(root, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = String(value ?? "—");
  root.append(term, detail);
}

/** @param {string} title @param {unknown} value */
function promptBlock(title, value) {
  const block = document.createElement("article");
  const heading = document.createElement("h3");
  heading.textContent = title;
  const text = document.createElement("p");
  text.textContent = String(value || "—");
  block.append(heading, text);
  return block;
}
