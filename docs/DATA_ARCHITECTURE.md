# ComfyReview Data Architecture

Status: canonical schema v4 is implemented for images, reviews, Arena and
Curation on the active refactor branch, 2026-09-30. Prompt components,
generation execution and some derived statistics remain transitional.

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

## 2. Canonical schema v4

The canonical database uses explicit schema metadata and foreign keys. Its
implemented cutover structures include:

- `generations` and normalized generation provenance;
- `images` with stable UID, current paths and `deleted_at`;
- append-only `review_events`;
- `arena_matches` referencing images;
- `curation_assignments` with one assignment per image;
- rebuildable current-state and aggregate views.

Unknown or unsupported versions fail at startup. Runtime startup never performs
a v3 to v4 migration. The explicit, backed-up command is:

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

The future canonical prompt catalog preserves authored material independently
of whether it has already produced an image. A stable prompt component owns
immutable prompt revisions. Changing positive text, negative text or explicit
weights creates a new revision; display name, tags and notes remain mutable
catalog metadata.

A prompt composition references concrete revision IDs. A generation references
the composition/revisions it used and also stores the exact rendered positive
and negative prompt snapshots. Catalog evolution therefore cannot reinterpret
historical generations. Deleting from the UI archives an item; it does not
destroy revisions or historical relationships.

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

Both import workflows complete validation before opening the write transaction
and create a SQLite backup before the first write. All accepted facts then
commit in exactly one transaction.

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
| `images.sqlite3` | rebuildable/verification projection for transitional features |
| `prompt_tokens.sqlite3` | legacy prompt projection; redesign instead of blind copy |
| `prompt_ratings.sqlite3` | transitional derived prompt statistics |
| `combo_prompts.sqlite3` | transitional eager combination projection |
| `playground.sqlite3` | pending prompt-component migration |
| `mv_jobs.sqlite3` | transitional worker/job state |

Legacy DDL remains centralized in
`comfyreview.repositories.sqlite.legacy_schema`. Normal legacy repositories
open existing files in `rw` mode and do not create schemas. Only entirely
missing files can be initialized during startup; invalid existing files abort.
Known additive changes require `python -m comfyreview legacy-db upgrade`.

## 10. Remaining canonical design

The target still needs normalized prompt/content components, compositions,
exact prompts and atom memberships, plus canonical operational job/projection
state. The design must not duplicate prompt atoms per review or materialize the
full Cartesian product of possible prompt combinations. Persist combinations
when they are explicitly authored or otherwise become domain-relevant. An
unused authored template or revision remains canonical catalog data.

Before migrating a derived projection, prefer a direct canonical query, then a
SQL view. Only measured needs justify a materialized projection and worker.

Character Chronicles may later reuse or extend this foundation, but its
descriptions, embeddings, RAG and gameplay state remain separate concerns.
