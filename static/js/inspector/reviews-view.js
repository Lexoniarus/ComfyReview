/** Render append-only canonical review events. */
export class ReviewsView {
  constructor() {
    this.element = document.createElement("section");
    this.element.className = "inspector-section inspector-reviews";
  }

  /** Show the review-history loading state. */
  loading() {
    this.#status("Bewertungshistorie wird geladen …");
  }

  /** @param {Array<Record<string, any>>} events */
  render(events) {
    const heading = document.createElement("h3");
    heading.textContent = `Reviews · ${events.length}`;
    const list = document.createElement("ol");
    list.className = "inspector-review-list";
    for (const event of events) {
      const item = document.createElement("li");
      const decision = document.createElement("strong");
      decision.textContent = eventLabel(event);
      const timestamp = document.createElement("time");
      timestamp.dateTime = String(event.reviewed_at || "");
      timestamp.textContent = formatTimestamp(event.reviewed_at);
      item.append(decision, timestamp);
      list.append(item);
    }
    if (!events.length) {
      const empty = document.createElement("p");
      empty.className = "inspector-empty";
      empty.textContent = "Noch keine Review-Events vorhanden.";
      this.element.replaceChildren(heading, empty);
      return;
    }
    this.element.replaceChildren(heading, list);
  }

  /** @param {string} message */
  error(message) {
    this.#status(
      message || "Bewertungshistorie konnte nicht geladen werden.",
      "is-error",
    );
  }

  /** @param {string} message @param {string} [className] */
  #status(message, className = "") {
    const heading = document.createElement("h3");
    heading.textContent = "Reviews";
    const status = document.createElement("p");
    status.className = `inspector-inline-status ${className}`.trim();
    status.textContent = message;
    this.element.replaceChildren(heading, status);
  }
}

/** @param {Record<string, any>} event */
function eventLabel(event) {
  if (event.event_type === "rating") return `Bewertung ${event.rating} / 10`;
  if (event.event_type === "delete") return "Gelöscht";
  if (event.event_type === "restore") return "Wiederhergestellt";
  return String(event.event_type || "Unbekanntes Event");
}

/** @param {unknown} value */
function formatTimestamp(value) {
  const text = String(value || "");
  const parsed = new Date(text.includes("T") ? text : text.replace(" ", "T"));
  return Number.isNaN(parsed.getTime())
    ? text || "Zeitpunkt unbekannt"
    : new Intl.DateTimeFormat("de-DE", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
}
