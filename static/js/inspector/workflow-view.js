/** Render canonical workflow provenance without exposing the raw graph. */
export class WorkflowView {
  constructor() {
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-workflow";
  }

  /** @param {Record<string, any>} image */
  render(image) {
    const workflow = image.workflow_provenance || {};
    const heading = document.createElement("h3");
    heading.textContent = "Workflow";
    const facts = document.createElement("dl");
    facts.className = "inspector-compact-facts";
    appendFact(facts, "Blueprint", blueprintLabel(workflow));
    appendFact(facts, "Graph-Hash", workflow.graph_hash);
    this.element.replaceChildren(heading, facts);
  }
}

/** @param {Record<string, any>} workflow */
function blueprintLabel(workflow) {
  if (!workflow.blueprint_uid) return "Legacy / unbekannt";
  const version = workflow.blueprint_version ?? "?";
  return `${workflow.blueprint_uid} · v${version}`;
}

/** @param {HTMLDListElement} root @param {string} label @param {unknown} value */
function appendFact(root, label, value) {
  const term = document.createElement("dt");
  term.textContent = label;
  const detail = document.createElement("dd");
  detail.textContent = String(value || "—");
  root.append(term, detail);
}
