# Canonical Review Storage

Status: canonical review/learning runtime with generation provenance and
image-output identity preparation. Slice 2A is based on branch head
`09d2b8aacf75cb8742f88fb58fb9686b17705eaf`.

## Purpose

The canonical SQLite database replaces the legacy review-time rating and
prompt-token journals as the normal review persistence path. Historical
SQLite files and generated PNG/JSON pairs remain migration inputs and are not
silently overwritten.

The normal runtime database is `data/comfyreview.sqlite3` and can be overridden
with `COMFYREVIEW_DATABASE`.

## Schema version 3

Schema version 3 separates a generation run from its output images.

A generation may now own multiple `images` rows. Every image has its own stable
`image_uid` and an explicit output slot consisting of `output_node_id` plus
`output_index`. The pair `(generation_id, output_node_id, output_index)` is
unique, while `generation_id` itself is deliberately not unique.

`images.json_path` is nullable. A JSON sidecar is therefore no longer a
canonical persistence requirement. The main review runtime now reads canonical
image rows before legacy filesystem discovery, so a registered PNG remains
reviewable even when no JSON sidecar exists.

Deleted output state is image-scoped as well. `deleted_images` stores the
`image_uid` and no longer assumes that deleting one output means deleting the
whole generation. Its `json_path` is nullable for the same reason.

Existing schema-v2 rows migrate as `output_node_id = legacy_sidecar` and
`output_index = 0`, preserving their image IDs, review foreign keys, paths and
generation relationships.

## Generation provenance

Schema version 2 already introduced:

- generation source
- raw metadata and exact workflow JSON slots
- workflow hash
- ComfyUI `prompt_id`
- lifecycle status and timestamps
- `generation_sampler_stages` for multiple KSampler stages

Those fields remain unchanged in version 3. Flat sampler columns remain only as
transitional compatibility and learning dimensions.

## Explicit canonical upgrade

Runtime startup never upgrades an existing canonical database silently.
Every older supported version must be upgraded into a separate output file:

```text
python -m comfyreview canonical-db upgrade --output data/comfyreview-v12.sqlite3
python -m comfyreview canonical-db validate
```

The upgrade creates a SQLite backup, migrates and validates the separate
output, and verifies that the source file did not change. Promotion of the
validated output is a separate controlled operation.

## Current review compatibility

Legacy sidecar-backed review remains operational, while canonical image records
can now be reviewed through stable `image_uid` even when `json_path` is NULL.
Canonical identities are preserved through rating/delete mutations instead of
being re-derived from filenames. Delete tombstones remain image-scoped.

The `ratings` and `tokens` compatibility views remain readable and are rebuilt
unchanged during the schema migration.

## Next step

Slice 3 imports the historical PNG/JSON corpus into canonical generation
provenance, preserving raw sidecars while treating the stored ComfyUI prompt
graph as historical render truth.

## Canonical-first output runtime

The main review runtime merges two sources:

1. live canonical `images` joined to their `generations` and exact prompts
2. legacy PNG/JSON discovery for historical files not yet represented in the
   canonical database

Canonical records win when both sources describe the same PNG. Their stable
`image_uid` and normalized generation facts are authoritative for rating and
delete operations. JSON sidecars are optional provenance, not identity.

Sidecarless canonical reviews do not enqueue the transitional legacy
materialized-view worker. Canonical review state and learning aggregates are
already updated inside the review transaction, while the legacy worker still
assumes a JSON path.
