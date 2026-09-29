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
canonical persistence requirement. The current filesystem catalog and review
HTTP boundary still require legacy PNG/JSON pairs; removing that runtime
requirement is the next, separate slice.

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
Version 1 or 2 must be upgraded explicitly:

```text
python -m comfyreview canonical-db upgrade
python -m comfyreview canonical-db validate
```

The upgrade creates a SQLite backup before mutation and restores it after an
ordinary migration failure. Version 1 can upgrade directly through version 2
to version 3 in one backed-up operation.

## Current review compatibility

The existing sidecar-backed review flow remains operational in Slice 2A. It
writes its current single legacy output into the new output model using the
`legacy_sidecar` output slot. Rating and delete learning semantics are
unchanged, except that delete tombstones are keyed by `image_uid` rather than
by generation.

The `ratings` and `tokens` compatibility views remain readable and are rebuilt
unchanged during the schema migration.

## Next step

Slice 2B moves live output discovery to a canonical DB-first image index and
changes the application boundary so a native ComfyUI output can be reviewed
without a JSON sidecar. Legacy filesystem sidecar discovery remains available
for import and transition.
