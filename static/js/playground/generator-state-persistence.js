/** Own durable, latest-write-wins persistence for Generator controls. */
export class GeneratorStatePersistence {
  /** @param {{api: {get: (path: string, options?: Record<string, any>) => Promise<any>, put: (path: string, body: unknown, options?: Record<string, any>) => Promise<any>}, snapshot: () => Record<string, any>, onError?: (error: unknown) => void, delay?: number}} dependencies */
  constructor(dependencies) {
    this.api = dependencies.api;
    this.snapshot = dependencies.snapshot;
    this.onError = dependencies.onError || (() => {});
    this.delay = dependencies.delay ?? 180;
    this.timer = null;
    this.writeTail = Promise.resolve();
    this.isDisposed = false;
  }

  load() {
    return this.api.get("playground/generator-state");
  }

  schedule() {
    if (this.isDisposed) return;
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => {
      this.timer = null;
      void this.save().catch((error) => this.onError(error));
    }, this.delay);
  }

  /** Persist the newest complete state after all earlier writes. */
  save() {
    return this.#queue(this.snapshot(), false);
  }

  /** Flush a pending change for navigation without bypassing the API module. */
  flush() {
    if (this.timer !== null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
    if (this.isDisposed) return this.writeTail;
    return this.#queue(this.snapshot(), true);
  }

  dispose() {
    this.isDisposed = true;
    if (this.timer !== null) window.clearTimeout(this.timer);
    this.timer = null;
  }

  /** @param {Record<string, any>} snapshot @param {boolean} keepalive */
  #queue(snapshot, keepalive) {
    const write = this.writeTail
      .catch(() => undefined)
      .then(() =>
        this.api.put("playground/generator-state", snapshot, { keepalive }),
      );
    this.writeTail = write;
    return write;
  }
}
