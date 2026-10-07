/** Translate durable compatibility fields at the persistence boundary. */
export class SamplerStateAdapter {
  /** @param {Record<string, any>} state */
  restore(state) {
    return {
      ...state,
      variant_count: state.variant_count ?? state.batch_runs ?? 1,
    };
  }

  /** @param {Record<string, any>} state */
  persist(state) {
    /** @type {Record<string, any>} */
    const persisted = {
      ...state,
      batch_runs: state.variant_count ?? state.batch_runs ?? 1,
    };
    delete persisted.variant_count;
    return persisted;
  }
}
