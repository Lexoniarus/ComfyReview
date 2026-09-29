# Canonical Review Storage

Status: canonical review/learning runtime with explicit generation-provenance
schema preparation, based on branch head
`0270fd8ebf8ba81eb2e3f1eaa1775a40d9d7c15e`.

## Purpose

The canonical SQLite database replaces the legacy review-time rating and
prompt-token journals as the normal review persistence path. Historical
`ratings.sqlite3` and `prompt_tokens.sqlite3` files remain legacy inputs and are
not silently imported or overwritten.

The normal runtime database is:

```text
data/comfyreview.sqlite3
```

Override it with `COMFYREVIEW_DATABASE` when required.

## Schema version 2

Schema version 2 prepares the generation record for the native ComfyUI runtime
boundary without changing the current review workflow yet.

Each `generations` row can now retain:

- a stable ComfyReview generation UID
- the current normalized render summary used by compatibility views
- generation source, defaulting to `legacy_sidecar` for the current path
- raw legacy metadata JSON for later provenance import
- the exact submitted ComfyUI API workflow JSON
- a workflow hash
- the ComfyUI `prompt_id`
- generation lifecycle status
- submitted, started and completed timestamps

A separate `generation_sampler_stages` table can represent every KSampler stage
in the submitted workflow. It is intentionally not limited to one sampler per
generation.

The existing flat sampler fields on `generations` remain during the transition
for compatibility and current learning queries. They are not the long-term
source of truth for complex workflows.

## Explicit canonical upgrade

Runtime startup does not silently mutate an existing schema-version-1 database.
A v1 database must be upgraded explicitly:

```text
python -m comfyreview canonical-db validate
python -m comfyreview canonical-db upgrade
python -m comfyreview canonical-db validate
```

An explicit backup directory may be supplied:

```text
python -m comfyreview canonical-db upgrade --backup-dir data/backups
```

The upgrade creates a SQLite backup before the first schema mutation. If the
migration fails, the backup is restored and the error is surfaced.

A missing canonical database is still initialized atomically at the current
schema version.

## Canonical facts

The canonical database currently stores:

- exact positive and negative prompts once
- normalized prompt atoms once
- ordered prompt membership with an explicit numeric weight
- generation metadata once per generation
- generation workflow/provenance slots for the upcoming native ComfyUI path
- zero or more normalized sampler-stage records per generation
- one live image location per generation in the current review slice
- one current review per live image
- one delete tombstone per deleted generation
- rebuildable aggregate learning state for prompt atoms and render parameters

File paths are attributes. Relations use integer IDs rather than paths as
identity.

The one-image-per-generation and mandatory-sidecar assumptions are still
transitional limitations. They are deliberately left unchanged in this slice
so the schema upgrade can be reviewed independently from output identity and
filesystem behavior.

## Prompt weights

Explicit weighted prompt syntax is normalized before persistence.

Example:

```text
(large bright cyan blue eyes:1.45)
```

is represented as:

```text
atom = large bright cyan blue eyes
weight_milli = 1450
```

The original segment is retained as `raw_text` for provenance. Unweighted
atoms use `weight_milli = 1000`.

The compatibility `tokens` view reconstructs the old token representation for
legacy read-only projections. No physical per-review token rows are written in
the canonical runtime.

## Review semantics

A rating is current state, not an append-only history.

Changing one image from rating 7 to rating 9 updates the same
`image_reviews` row. The learning aggregates subtract the old contribution and
add the new contribution in the same SQLite transaction.

The monotonically increasing review version exists only to invalidate and
refresh transitional read projections. It is not a count of independent user
opinions.

## Delete semantics

Deleting an image removes its live `images` and `image_reviews` relation.
A small `deleted_images` tombstone remains so transitional projections can
remove stale gallery rows and so one negative learning observation can be
retained.

The aggregate learning state therefore remembers that a generation was
rejected without retaining a live image relation. If the same generation later
reappears and is rated again, the delete contribution is removed before the
new rating is applied.

## Compatibility views

Two read-only views preserve the old query shape while remaining code is moved
to the canonical model:

- `ratings`
- `tokens`

The views are generated from canonical facts. They are not writable journals.
Legacy aggregate pages and the transitional worker may read them during the
cutover.

## Projection worker

The transitional MV worker rebuilds prompt-rating and image projections after
a debounced catchup request instead of assuming that every rating creates a
new physical ratings row.

This favors correctness during the cutover. The canonical aggregate tables are
the intended basis for the later optimized learning queries.

## Legacy isolation

The normal review runtime does not use the historical root-level ratings/token
databases. Bootstrap gives the still-unmigrated legacy lifecycle small
compatibility databases below:

```text
data/_legacy_runtime/
```

The explicit legacy validation/upgrade CLI can still address the historical
settings for audit or later import work.

## Deliberate transition limits

This slice does not yet:

- import existing PNG/sidecar outputs into canonical generation provenance
- populate `generation_sampler_stages` from old `comfy_prompt_graph` payloads
- make JSON sidecars optional for live output discovery
- allow multiple output images per generation in the review model
- submit generations through a new `ComfyUiProvider`
- track ComfyUI WebSocket progress or completion
- replace workflow patching with a semantic workflow compiler
- remove the custom ComfyReview node from the default workflow
- import old rating/token history
- normalize Playground components into `prompt_components` and
  `component_atoms`
- give Arena its final pairwise-learning model
- move all old derived databases into the canonical file

Those items are follow-up vertical slices. The important change in schema v2 is
that the canonical generation record now has a place for the exact workflow
and external execution identity instead of forcing all future provenance into
the old flat sidecar summary.
