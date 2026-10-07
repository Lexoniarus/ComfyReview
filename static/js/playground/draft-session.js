/** Own one reviewed draft and all prepare/submit request transitions. */
export class DraftSession {
  /** @param {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} requests */
  constructor(requests) {
    this.requests = requests;
    this.phase = "idle";
    this.draftUid = "";
    this.revision = 0;
  }

  get isReady() {
    return this.phase === "ready" && Boolean(this.draftUid);
  }

  invalidate() {
    this.revision += 1;
    this.requests.cancelRequests();
    this.phase = "idle";
    this.draftUid = "";
  }

  /** @param {(signal: AbortSignal) => Promise<Record<string, any>>} operation */
  async prepare(operation) {
    this.invalidate();
    const revision = this.revision;
    this.phase = "preparing";
    try {
      const draft = await this.requests.run(operation);
      if (revision !== this.revision) {
        throw new DOMException("Draft is stale", "AbortError");
      }
      const draftUid = String(draft?.draft_uid || "").trim();
      if (!draftUid)
        throw new Error("Der Server hat keine Draft-ID geliefert.");
      this.draftUid = draftUid;
      this.phase = "ready";
      return draft;
    } catch (error) {
      if (revision === this.revision) {
        this.phase = "idle";
        this.draftUid = "";
      }
      throw error;
    }
  }

  /** @template T @param {(signal: AbortSignal) => Promise<T>} operation */
  async submit(operation) {
    if (!this.isReady) throw new Error("Der Entwurf ist nicht mehr gültig.");
    const revision = this.revision;
    this.phase = "submitting";
    try {
      const result = await this.requests.run(operation);
      if (revision !== this.revision) {
        throw new DOMException("Draft is stale", "AbortError");
      }
      this.phase = "ready";
      return result;
    } catch (error) {
      if (revision === this.revision) this.phase = "ready";
      throw error;
    }
  }

  dispose() {
    this.invalidate();
    this.requests.dispose();
  }
}
