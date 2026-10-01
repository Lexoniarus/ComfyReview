/** Own in-flight requests and timers for one browser component. */
export class RequestLifecycle {
  constructor() {
    /** @type {Set<AbortController>} */
    this.controllers = new Set();
    /** @type {Set<number>} */
    this.timers = new Set();
    this.isDisposed = false;
  }

  /**
   * Run one abortable operation while this owner is active.
   * @template T
   * @param {(signal: AbortSignal) => Promise<T>} operation
   * @returns {Promise<T>}
   */
  async run(operation) {
    if (this.isDisposed) {
      throw new DOMException("Request owner is disposed", "AbortError");
    }
    const controller = new AbortController();
    this.controllers.add(controller);
    try {
      return await operation(controller.signal);
    } finally {
      this.controllers.delete(controller);
    }
  }

  /** @param {() => void} callback @param {number} delay */
  schedule(callback, delay) {
    if (this.isDisposed) {
      return null;
    }
    const timer = window.setTimeout(() => {
      this.timers.delete(timer);
      if (!this.isDisposed) {
        callback();
      }
    }, delay);
    this.timers.add(timer);
    return timer;
  }

  /** @param {number | null} timer */
  cancel(timer) {
    if (timer === null) {
      return;
    }
    window.clearTimeout(timer);
    this.timers.delete(timer);
  }

  /** Abort active requests while keeping this lifecycle reusable. */
  cancelRequests() {
    for (const controller of this.controllers) {
      controller.abort();
    }
    this.controllers.clear();
  }

  /** Abort every owned request and clear every owned timer. */
  dispose() {
    if (this.isDisposed) {
      return;
    }
    this.isDisposed = true;
    this.cancelRequests();
    for (const timer of this.timers) {
      window.clearTimeout(timer);
    }
    this.timers.clear();
  }
}
