# ComfyReview Data Architecture

Status: canonical schema v6 and the live historical-data completion are
implemented for images, reviews, Arena, Curation, revisioned prompts and
native generation outputs on the active refactor branch, 2026-10-01.
Playground catalog editing remains transitional.

## 1. Source-of-truth rule

Every business fact has one writable authoritative home. Review, Arena and
Curation runtime writes now go only to `comfyreview.sqlite3`; the old files are
read-only import sources for these concerns. There are no dual-writes.

Stable IDs are identity. Paths are mutable evidence and file attributes:

```text
image_uid = "..."
png_path = "E:/ComfyUI/output/.../image.png"
```

Changing a path does not change the image UID or any review, match or curation
relationship.

## 2. Canonical schema v6

The canonical database uses explicit schema metadata and foreign keys. Schema
v6 contains the v4 identity/review cutover, the v5 prompt catalog and native
output provenance:

- `generations` and normalized generation provenance;
- `images` with stable UID, output role, content hash, current paths and
  `deleted_at`;
- append-only `review_events`;
- `arena_matches` referencing images;
- `curation_assignments` with one assignment per image;
- `prompt_components` with stable component UIDs and mutable metadata;
- immutable `prompt_revisions`;
- `prompt_compositions` and their concrete revision membership;
- rebuildable current-state and aggregate views.

Unknown or unsupported versions fail at startup. Runtime startup never performs
a v3-to-v4, v4-to-v5 or v5-to-v6 migration. The explicit, backed-up command is:

```text
python -m comfyreview canonical-db upgrade [--backup-dir PATH]
```

## 3. Review history and current state

Schema v4 intentionally changes reviews from a writable current-state table to
an append-only canonical history. Each `review_events` row has a stable event
UID, image relation, event type, optional rating, source, idempotent source key,
canonical sequence and available source timestamp.

Event semantics:

- `rating` appends a score;
- `delete` records the decision and makes the image non-live;
- rating a deleted image appends `restore` and then `rating` atomically;
- `restore` makes the image live without erasing history.

`images.deleted_at` is updated in the same transaction for efficient runtime
queries, but is a projection of the event history rather than a competing
truth. The current score is the latest effective rating after the last
lifecycle boundary. Rating count and average are derived from rating events;
live rankings exclude deleted images.

`current_image_reviews`, `image_review_summary`, `image_reviews` and
`deleted_images` are read-only views. The latter two preserve legacy query
shapes only. No repository may write to them, and all projections can be rebuilt
from `review_events` and canonical image facts.

## 4. Image and generation provenance

A generation and each output image have separate stable identities. Existing
UIDs survive imports. New historical images and generations receive
content-derived identities; file paths are deliberately excluded from identity.

Generation provenance may include raw sidecar metadata, workflow content and
hash, normalized prompts, checkpoint, LoRAs and ordered sampler stages.
Enriching an existing generation does not replace its source, lifecycle,
ComfyUI prompt ID, timestamps or occupied output slots.

The ComfyUI graph remains the render source of truth. Raw payloads are retained
for provenance and future parsing; application queries use normalized fields.

## 5. Arena and Curation

Arena facts relate `left_image_id`, `right_image_id` and `winner_image_id`.
The match and its generated rating events commit in one canonical transaction.
Directed rematches retain the existing product behavior.

Curation relates one image to an optional set key. A filesystem move happens
outside the SQLite write transaction. After a successful move, current image
paths and the assignment update atomically. A database failure causes a
best-effort filesystem rollback; rollback failures are separately visible.

Sidecars are optional for already-canonical images. Review, Top/Worst, Arena,
Curation and Delete therefore work for canonical PNGs without sidecars.

## 5.1 Prompt catalog revisions

The canonical prompt catalog preserves authored material independently
of whether it has already produced an image. A stable prompt component owns
immutable prompt revisions. Changing positive text, negative text or explicit
weights creates a new revision; display name, tags and notes remain mutable
catalog metadata.

A prompt composition references concrete revision IDs. A generation references
the composition/revisions it used and also stores the exact rendered positive
and negative prompt snapshots. Catalog evolution therefore cannot reinterpret
historical generations. Deleting from the UI archives an item; it does not
destroy revisions or historical relationships.

`PromptCatalogService` owns catalog use cases through an injected repository;
SQLite and stable-ID generation remain technical adapters. Playground preview
selection and rendering now consume exact catalog revisions and retain their
UIDs in each draft. A manual draft edit changes only its rendered snapshot. It
does not create or mutate a revision. Playground submission uses the native
`GenerationService`, preserves exact prompt snapshots and revision IDs, and
does not dual-write legacy generation state.

Legacy prompt migration is explicit:

```text
python -m comfyreview legacy-prompts audit
python -m comfyreview legacy-prompts import [--backup-dir PATH]
```

The audit binds both databases by SHA-256 and reads the source in SQLite
read-only mode. The import revalidates the snapshot, creates a backup and
writes the complete accepted set in one transaction. It is idempotent, retains
unused items and never mutates the source database.

Historical generation-to-composition completion is a separate explicit step:

```text
python -m comfyreview legacy-compositions audit
python -m comfyreview legacy-compositions import [--backup-dir PATH]
```

The version-2 audit considers every immutable canonical revision and recognizes
complete positive/negative prompt-atom sequences. Historical compositions may
contain any non-empty, ordered subset of catalog slots; the importer does not
require all catalog kinds to be present. A slot is accepted only when its
revision match is unique and consistent. Additional historical prompt text is
retained solely in the unchanged generation snapshot and is classified as a
draft override rather than invented as a component or revision.

Results are classified as `already_exact`, `exactly_reconstructable`,
`reconstructable_with_draft_override`, `ambiguous`, `insufficient_evidence` or
`conflict`. Both reconstructable categories may be linked. Ambiguous or
incomplete evidence never creates a guessed relationship. Composition UIDs are
derived from ordered slot, position and revision-UID tuples; paths are not
involved. Audit format version 2 prevents the discarded fixed-slot report from
being imported.

The completed 2026-10-01 live run linked 363 of 379 generations: 29 rendered
exactly from their recovered memberships and 334 retained additional historical
draft text in the canonical prompt snapshot. Sixteen generations remain
unlinked: two have ambiguous expression evidence and fourteen have no
sufficient catalog evidence. There were no conflicts. These are observed data
results, not hard-coded importer expectations.

## 6. Audited historical output import

Historical output migration has two explicit steps:

```text
python -m comfyreview legacy-output audit
python -m comfyreview legacy-output import [--backup-dir PATH]
```

The audit fingerprints the canonical database plus PNGs, sidecars and workflow
graphs. The importer validates the report structure and UID assignments, then
recomputes hashes immediately before any write. Missing files, changed content,
unknown samplers, partial graphs and UID/path/output-slot collisions abort the
whole import. PNGs without sidecars are reported separately and are not
invented as canonical records. Source PNGs and sidecars are never modified.

The accepted import writes all provenance and sampler stages in one SQLite
transaction after creating a backup. Canonical readers use a genuine
SQLite `mode=ro` connection.

## 7. Audited legacy feature import

Ratings, Arena and Curation use their own audit/import workflow:

```text
python -m comfyreview legacy-features audit
python -m comfyreview legacy-features import [--backup-dir PATH]
```

All source databases are opened read-only and bound to the report by SHA-256.
Legacy paths are used only to resolve an existing canonical image UID; no UID is
derived from a path. Existing canonical v3 reviews are deduplicated against
matching source facts. Ambiguous or contradictory mappings block the import.
Historical missing images and dependent facts are reported as orphans.

The importer is idempotent, validates aggregate parity and writes ratings,
matches and assignments in one canonical transaction. Observed source counts
are operational control values, not hard-coded schema expectations.

## 8. Backup, rollback and restore

Every import workflow completes validation before opening the write
transaction and creates a SQLite backup before the first write. All accepted
facts for that import then commit in exactly one transaction. A fresh audit and
new backup are required after each preceding import because the canonical hash
has changed.

On an ordinary exception the transaction is rolled back first. The production
database is validated after rollback and is not overwritten merely because an
exception occurred. A physical restore is attempted only when validation fails,
an out-of-transaction structural change took effect or the commit state cannot
be established. Restore errors remain distinguishable from the original error.

Reports, backups and runtime databases are local artifacts ignored by Git.

## 9. Legacy databases during transition

| Legacy database | Current treatment |
| --- | --- |
| `ratings.sqlite3` | read-only review import source; not Review runtime truth |
| `arena.sqlite3` | read-only Arena import source; not Arena runtime truth |
| `curation.sqlite3` | read-only Curation import source; not Curation runtime truth |
| `images.sqlite3` | historical feature-import evidence only |
| `prompt_tokens.sqlite3` | historical projection retained only for explicit maintenance |
| `prompt_ratings.sqlite3` | historical derived statistics retained only for explicit maintenance |
| `combo_prompts.sqlite3` | historical eager projection retained only for explicit maintenance |
| `playground.sqlite3` | audited prompt-import source only |
| `mv_jobs.sqlite3` | historical worker/job database; no runtime consumer |

Legacy DDL remains centralized in
`comfyreview.repositories.sqlite.legacy_schema`. Legacy paths are loaded through
`LegacyMigrationSettings`, which is not part of the application container.
Normal runtime startup neither opens nor initializes these files. Known
additive changes require the explicit `python -m comfyreview legacy-db upgrade`
command.

## 10. Completed canonical data migration and remaining design

The live schema-v6 database now contains 379 generations, 379 images, 379
sampler stages, 729 prompt components, 729 immutable first revisions, 275
recovered compositions and 1,280 ordered composition memberships. All 379
images have output role, output index and a verified content hash. The existing
5,468 review events, 1,224 Arena matches and three Curation assignments remain
canonical facts.

Completion was rehearsed from a verified v4 backup through the full v4-to-v6
upgrade and all four fresh audit/import stages. The same ordered sequence then
ran against the already-upgraded live v6 database. Each live import created its
own validated backup before writing. Final `integrity_check`, foreign-key,
schema, identity, protected-field, provenance, read-only-reader and
canonical-only startup checks passed. Repeated rehearsal imports created no
additional facts.

Normal startup never performs this sequence and never opens a legacy database.
The ignored detailed reports and backups remain the operational evidence; this
document records only non-sensitive aggregate results.

The design must not duplicate prompt atoms per review or materialize the full
Cartesian product of possible prompt combinations. Persist combinations when
they are explicitly authored, generated, curated or uniquely reconstructed. An
unused authored template or revision remains canonical catalog data.

Frontend V2 scope work may now begin. Exact memberships are authoritative for
the 363 linked generations. Any scope fallback for the sixteen unresolved
generations must be the smallest read-only policy justified by their explicit
diagnostics; it must not read legacy databases, paths, directory names or
sidecars as runtime truth.

Before migrating a derived projection, prefer a direct canonical query, then a
SQL view. Only measured needs justify a materialized projection and worker.

Character Chronicles may later reuse or extend this foundation, but its
descriptions, embeddings, RAG and gameplay state remain separate concerns.
