/** @typedef {{groups: (options?: {signal?: AbortSignal}) => Promise<any>}} GroupApi */
/** @typedef {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, schedule: (callback: () => void, delay: number) => number|null, cancel: (timer: number|null) => void, cancelRequests: () => void, dispose: () => void}} RequestBoundary */

const sections = [
  ["running", "Läuft"],
  ["ready", "Vergleichsbereit"],
  ["partial", "Teilweise fehlgeschlagen"],
  ["completed", "Abgeschlossen"],
  ["rejected", "Verworfen"],
];

/** Own the grouped Candidate-set overview and its bounded polling lifecycle. */
export class CardCandidateGroupOverview {
  /** @param {{root: HTMLElement, api: GroupApi, requests: RequestBoundary, pollInterval?: number}} dependencies */
  constructor(dependencies) {
    this.root = dependencies.root;
    this.api = dependencies.api;
    this.requests = dependencies.requests;
    this.pollInterval = dependencies.pollInterval || 2000;
    this.status = requiredElement(this.root, "[data-group-overview-status]");
    this.content = requiredElement(this.root, "[data-group-overview-content]");
    this.timer = null;
  }

  /** Load all groups and begin polling while external work is active. */
  async start() {
    await this.reload();
  }

  /** Refresh all server-projected group states once. */
  async reload() {
    this.requests.cancel(this.timer);
    this.timer = null;
    try {
      const payload = await this.requests.run((signal) =>
        this.api.groups({ signal }),
      );
      /** @type {Array<Record<string, any>>} */
      const groups = Array.isArray(payload.items) ? payload.items : [];
      this.#render(groups);
      this.status.textContent = `${groups.length} Candidate-Gruppen`;
      if (groups.some((group) => isRunning(String(group.status)))) {
        this.timer = this.requests.schedule(
          () => void this.reload(),
          this.pollInterval,
        );
      }
    } catch (error) {
      if (!isAbortError(error)) {
        this.content.replaceChildren(
          message("card-error-state", errorMessage(error)),
        );
        this.status.textContent = "Gruppen konnten nicht geladen werden";
      }
    }
  }

  /** Dispose polling timers and requests. */
  dispose() {
    this.requests.cancel(this.timer);
    this.requests.dispose();
  }

  /** @param {Array<Record<string, any>>} groups */
  #render(groups) {
    if (!groups.length) {
      this.content.replaceChildren(
        message(
          "card-empty-state",
          "Noch keine Candidate-Gruppe. Wähle zuerst ein Quellbild aus.",
        ),
      );
      return;
    }
    this.content.replaceChildren(
      ...sections.map(([key, label]) =>
        this.#section(
          key,
          label,
          groups.filter((group) => bucket(String(group.status)) === key),
        ),
      ),
    );
  }

  /** @param {string} key @param {string} label @param {Array<Record<string, any>>} groups */
  #section(key, label, groups) {
    const section = document.createElement("section");
    section.className = "candidate-group-lane";
    section.dataset.groupLane = key;
    const header = document.createElement("header");
    const heading = document.createElement("h2");
    heading.textContent = label;
    const count = document.createElement("span");
    count.className = "candidate-group-count";
    count.textContent = String(groups.length);
    header.append(heading, count);
    const grid = document.createElement("div");
    grid.className = "candidate-group-grid";
    grid.replaceChildren(
      ...(groups.length
        ? groups.map((group) => this.#group(group))
        : [message("candidate-group-empty", "Keine Gruppen")]),
    );
    section.append(header, grid);
    return section;
  }

  /** @param {Record<string, any>} group */
  #group(group) {
    const anchor = document.createElement("a");
    anchor.className = "candidate-group-tile";
    anchor.href = `/card-candidate-groups/${encodeURIComponent(String(group.group_id))}`;
    anchor.dataset.status = String(group.status || "unknown");
    const image = document.createElement("img");
    image.src = String(group.source?.image_url || "");
    image.alt = "Ursprungsbild der Candidate-Gruppe";
    image.loading = "lazy";
    const body = document.createElement("span");
    body.className = "candidate-group-tile-body";
    const kind = document.createElement("small");
    kind.textContent =
      group.kind === "development" ? "ENTWICKLUNG" : "ERSTELLUNG";
    const title = document.createElement("strong");
    title.textContent = statusLabel(String(group.status));
    const progress = document.createElement("span");
    progress.className = "candidate-group-progress";
    const candidates = Array.isArray(group.candidates) ? group.candidates : [];
    const terminal = candidates.filter((candidate) =>
      ["completed", "failed", "accepted", "rejected"].includes(
        String(candidate.status),
      ),
    ).length;
    progress.textContent = `${terminal} / 4 Slots terminal`;
    body.append(kind, title, progress);
    anchor.append(image, body);
    return anchor;
  }
}

/** @param {string} status */
function bucket(status) {
  if (isRunning(status)) return "running";
  if (status === "ready") return "ready";
  if (status === "partial_failure" || status === "failed") return "partial";
  if (status === "completed") return "completed";
  return "rejected";
}

/** @param {string} status */
function isRunning(status) {
  return ["queued", "composing", "generating"].includes(status);
}

/** @param {string} status */
function statusLabel(status) {
  return (
    {
      queued: "Eingereiht",
      composing: "Karten werden aufgebaut",
      generating: "Bilder werden erzeugt",
      ready: "Vier Karten bereit",
      partial_failure: "Teilweise bereit",
      failed: "Gruppe fehlgeschlagen",
      completed: "Karte angenommen",
      rejected: "Satz verworfen",
    }[status] || status
  );
}

/** @param {ParentNode} root @param {string} selector */
function requiredElement(root, selector) {
  const element = root.querySelector(selector);
  if (!(element instanceof HTMLElement)) throw new Error(`Missing ${selector}`);
  return element;
}

/** @param {string} className @param {string} text */
function message(className, text) {
  const paragraph = document.createElement("p");
  paragraph.className = className;
  paragraph.textContent = text;
  return paragraph;
}

/** @param {unknown} error */
function isAbortError(error) {
  return error instanceof DOMException && error.name === "AbortError";
}

/** @param {unknown} error */
function errorMessage(error) {
  return error && typeof error === "object" && "message" in error
    ? String(error.message)
    : "Die Anfrage ist fehlgeschlagen.";
}
