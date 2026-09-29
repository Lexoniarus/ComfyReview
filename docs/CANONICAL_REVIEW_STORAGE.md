# Canonical Review Storage

Status: first canonical review/learning slice for
`refactor/review-boundary`, based on branch head
`93d9f58fbe10ad1adbb247440d2f8db04cb76385`.

## Purpose

This slice replaces the legacy review-time prompt-token journal with one
canonical SQLite database. Historical `ratings.sqlite3` and
`prompt_tokens.sqlite3` files are not imported or overwritten.

The normal runtime database is:

```text
data/comfyreview.sqlite3
```

Override it with `COMFYREVIEW_DATABASE` when required.

## Canonical facts

The canonical database stores:

- exact positive and negative prompts once
- normalized prompt atoms once
- ordered prompt membership with an explicit numeric weight
- generation metadata once per generation
- one live image location per generation
- one current review per live image
- one delete tombstone per deleted generation
- rebuildable aggregate learning state for prompt atoms and render parameters

File paths are attributes. Relations use integer IDs rather than paths as
identity.

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

- import old rating/token history
- normalize Playground components into `prompt_components` and
  `component_atoms`
- give Arena its final pairwise-learning model
- move all old derived databases into the canonical file
- persist a ComfyUI-provided stable generation UUID or seed when the current
  sidecar does not expose it through the review boundary

Those are follow-up vertical slices. The review path itself no longer requires
legacy rating or token journals.
