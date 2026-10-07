/** Own one transient variant batch, selection and request lifecycle. */
export class VariantSession {
  /** @param {{run: <T>(operation: (signal: AbortSignal) => Promise<T>) => Promise<T>, cancelRequests: () => void, dispose: () => void}} requests @param {() => void} [onChange] */
  constructor(requests, onChange = () => {}) {
    this.requests = requests;
    this.onChange = onChange;
    this.phase = "idle";
    this.revision = 0;
    this.stale = false;
    /** @type {Array<Record<string, any>>} */
    this.variants = [];
    this.selectedDraftUids = new Set();
    this.activeDraftUid = "";
    this.metadata = emptyMetadata();
    /** @type {Map<string, Record<string, any>>} */
    this.reviewedPayloads = new Map();
  }

  get hasVariants() {
    return this.variants.length > 0;
  }

  get canSubmit() {
    return (
      this.phase === "ready" && !this.stale && this.selectedDraftUids.size > 0
    );
  }

  snapshot() {
    return {
      phase: this.phase,
      stale: this.stale,
      variants: this.variants,
      selectedDraftUids: new Set(this.selectedDraftUids),
      activeDraftUid: this.activeDraftUid,
      metadata: { ...this.metadata },
    };
  }

  activeVariant() {
    return this.variants.find(
      (variant) => String(variant.draft_uid) === this.activeDraftUid,
    );
  }

  selectedVariants() {
    return this.variants.filter((variant) =>
      this.selectedDraftUids.has(String(variant.draft_uid)),
    );
  }

  /** @param {string} draftUid */
  inspect(draftUid) {
    if (!this.#has(draftUid)) return false;
    this.activeDraftUid = draftUid;
    this.onChange();
    return true;
  }

  /** @param {string} draftUid @param {boolean} selected */
  select(draftUid, selected) {
    if (!this.#has(draftUid)) return false;
    if (selected) this.selectedDraftUids.add(draftUid);
    else this.selectedDraftUids.delete(draftUid);
    this.onChange();
    return true;
  }

  /** @param {string} draftUid @param {Record<string, any>} payload */
  review(draftUid, payload) {
    if (!this.#has(draftUid)) return false;
    this.reviewedPayloads.set(draftUid, payload);
    this.onChange();
    return true;
  }

  /** @param {string} draftUid */
  reviewedPayload(draftUid) {
    return this.reviewedPayloads.get(draftUid) || null;
  }

  markStale() {
    this.revision += 1;
    this.requests.cancelRequests();
    if (!this.hasVariants) return;
    this.stale = true;
    this.phase = "ready";
    this.onChange();
  }

  /** @param {(signal: AbortSignal) => Promise<Record<string, any>>} operation */
  async prepare(operation) {
    this.revision += 1;
    this.requests.cancelRequests();
    const revision = this.revision;
    this.phase = "preparing";
    this.onChange();
    try {
      const batch = await this.requests.run(operation);
      if (revision !== this.revision)
        throw new DOMException("Variant batch is stale", "AbortError");
      this.#replace(batch);
      return batch;
    } catch (error) {
      if (revision === this.revision) {
        this.phase = this.hasVariants ? "ready" : "idle";
        this.onChange();
      }
      throw error;
    }
  }

  /** @template T @param {(signal: AbortSignal) => Promise<T>} operation */
  async submit(operation) {
    if (!this.canSubmit)
      throw new Error("Die ausgewählten Varianten sind nicht generierbar.");
    const revision = this.revision;
    this.phase = "submitting";
    this.onChange();
    try {
      const result = await this.requests.run(operation);
      if (revision !== this.revision)
        throw new DOMException("Variant batch is stale", "AbortError");
      this.phase = "ready";
      this.onChange();
      return result;
    } catch (error) {
      if (revision === this.revision) {
        this.phase = "ready";
        this.onChange();
      }
      throw error;
    }
  }

  dispose() {
    this.revision += 1;
    this.requests.cancelRequests();
    this.requests.dispose();
    this.phase = "idle";
    this.variants = [];
    this.selectedDraftUids.clear();
    this.reviewedPayloads.clear();
    this.activeDraftUid = "";
  }

  /** @param {Record<string, any>} batch */
  #replace(batch) {
    const variants = Array.isArray(batch?.variants) ? batch.variants : [];
    const draftUids = variants.map((variant) =>
      String(variant?.draft_uid || "").trim(),
    );
    if (
      !draftUids.length ||
      draftUids.some((draftUid) => !draftUid) ||
      new Set(draftUids).size !== draftUids.length
    )
      throw new Error(
        "Der Server hat keinen gültigen Varianten-Batch geliefert.",
      );
    this.variants = variants;
    this.selectedDraftUids = new Set(draftUids);
    this.activeDraftUid = draftUids[0];
    this.reviewedPayloads.clear();
    this.metadata = {
      requestedCount: Number(batch.requested_count || variants.length),
      uniqueCount: Number(batch.unique_count || variants.length),
      repeatedCount: Number(batch.repeated_count || 0),
      diversityExhausted: Boolean(batch.diversity_exhausted),
      notice: String(batch.notice || ""),
    };
    this.stale = false;
    this.phase = "ready";
    this.onChange();
  }

  /** @param {string} draftUid */
  #has(draftUid) {
    return this.variants.some(
      (variant) => String(variant.draft_uid) === draftUid,
    );
  }
}

function emptyMetadata() {
  return {
    requestedCount: 0,
    uniqueCount: 0,
    repeatedCount: 0,
    diversityExhausted: false,
    notice: "",
  };
}
