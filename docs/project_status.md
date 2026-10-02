# Project Status

## Summary

ComfyReview is a local-first FastAPI workflow tool for reviewing, comparing,
curating, analysing and reproducibly regenerating ComfyUI outputs. The active
refactor branch uses one canonical writable SQLite database and a native
ES-module Frontend V2.

## Implemented state

- canonical schema v8 with stable image/generation identity;
- append-only Review events and rebuildable current-state/ranking views;
- UID-based Arena and Curation;
- audited, idempotent historical Output, Prompt, Feature and Composition
  imports;
- immutable prompt revisions, structured weighted atoms and reproducible
  compositions;
- versioned workflow blueprints, dedicated compiler and technical ComfyUI
  provider;
- generation lifecycle, reconciliation, multi-output collection and normalized
  sampler/LoRA provenance;
- canonical Analytics for Scopes, parameters, prompt combinations and observed
  render setups;
- Frontend V2 for Review, Top/Worst, Arena, Playground, Catalog, Generations,
  Analytics and Settings;
- workspace preferences and reusable generation profiles with ordered LoRA
  stacks;
- shared Python/frontend quality gate with architecture tests, coverage and
  Playwright browser acceptance.

## Runtime rules

Normal runtime reads and writes only the canonical database. Legacy databases,
sidecars and path relationships are available solely to explicit offline
audit/import tools. Paths are attributes, not identity, and no cut-over feature
dual-writes legacy state.

New generation uses standard ComfyUI output nodes plus Blueprint v2. The
compiler owns prompt, sampler, output-role and LoRA graph semantics; the
provider owns only transport, job state, capabilities and raw output
descriptors.

## Remaining acceptance

The implementation slices are complete on `refactor/review-boundary`. Remaining
work before the replacement pull request is user-facing visual acceptance, an
optional real-ComfyUI smoke generation, the final dead-path usage audit and
integration review. The branch is intentionally not merged automatically.

## Scope and limitations

ComfyReview remains a local tool rather than a hosted multi-user service or a
packaged desktop installer. Infrastructure paths and the ComfyUI endpoint are
still configured through the local environment. Historical imports need their
retained evidence; already-canonical sidecarless images remain usable. Export
and dataset-packaging workflows are not final production pipelines.

Project code is licensed under the MIT License. See `LICENSE`.
