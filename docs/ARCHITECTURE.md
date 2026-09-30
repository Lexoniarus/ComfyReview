# ComfyReview Architecture

Status: canonical Review, Ranking, Arena and Curation cutover plus the
revisioned prompt-catalog boundary are implemented on the active refactor
branch, 2026-09-30. Generation, Playground submission and parts of the
statistics/projection pipeline remain transitional.

## 1. Product boundary

ComfyReview is a local-first application for discovering ComfyUI outputs,
reviewing and comparing images, assigning curated sets, analysing review data
and handing reproducible settings back to ComfyUI. Character Chronicles
gameplay, embeddings and RAG are outside this refactor unless added explicitly.

## 2. Layering and composition

```text
Browser / Jinja
      |
FastAPI routes
      |
Application services and typed ports
      |
Repositories                 Providers
(canonical SQLite)           (filesystem / ComfyUI)
```

Routes translate HTTP data only. Stateful repositories, providers and workers
are classes. SQL is confined to SQLite repositories and explicit offline
migration adapters. Filesystem changes are owned by providers/adapters, and
application services coordinate them without holding a SQLite write
transaction open.

`comfyreview.bootstrap.create_app()` is the composition root. Its
`ApplicationContainer` owns typed settings, canonical and legacy schema
lifecycles, the transitional worker runtime, the canonical output catalog and
the Review, Ranking, Arena and Curation services. The FastAPI lifespan prepares
directories, validates supported schemas, starts the worker and performs a
bounded stop. Root `app.py` and `main.py` remain compatible entry points.

## 3. Canonical identity and runtime data

The canonical database has an explicit schema version. Schema v5 is the active
shape: it retains the v4 identity/review cutover and adds the revisioned prompt
catalog. Stable `image_uid` and `generation_uid` values are identity; PNG and
optional sidecar paths are mutable attributes.

Canonical v4 facts include:

- images and generation provenance;
- append-only `review_events`;
- `arena_matches` linked to images;
- one `curation_assignments` relation per image.

Canonical v5 additionally includes stable prompt components, immutable prompt
revisions, explicit compositions and source mappings for audited legacy
imports. Catalog metadata can change without rewriting revision content.

`images.deleted_at`, `current_image_reviews`, `image_review_summary` and ranking
results are projections derived from canonical facts. The old `image_reviews`
and `deleted_images` names exist only as read-only compatibility views. No
repository writes a second current-review truth.

The following legacy databases remain available only where an unmigrated
feature still needs them or as read-only import sources:

```text
ratings.sqlite3          arena.sqlite3
curation.sqlite3         playground.sqlite3
prompt_tokens.sqlite3    prompt_ratings.sqlite3
images.sqlite3           combo_prompts.sqlite3
mv_jobs.sqlite3
```

There are no Review, Arena or Curation dual-writes between these files and the
canonical database.

## 4. Review semantics

`review_events` is deliberately an append-only canonical history. This is an
explicit evolution from the previous current-state model.

- `rating` records a score.
- `delete` records the decision and sets the lifecycle projection.
- rating a deleted image atomically appends `restore` followed by `rating`.
- `images.deleted_at` changes in the same transaction but remains rebuildable
  from events.
- the current score is the latest effective rating after the last lifecycle
  boundary.
- averages and counts are calculated from rating events; deleted images are
  excluded from live rankings.

Review commands use `image_uid`. The canonical image resolver loads the current
path and generation data server-side. A sidecar is optional for an already
canonical image. Delete stages the current files reversibly, writes the event,
and then finalizes the staged deletion. Ordinary failures trigger compensation
and remain visible.

`SqliteReviewRepository` accepts only an existing image/generation identity; a
review can neither create nor rewrite generation or image provenance. Prompt
normalization belongs to catalog/generation persistence, not to the review
transaction. Legacy token repair is isolated from the Review application port.

## 5. Ranking and Arena

`RankingService.list_images()` reads canonical images, review aggregates and
curation state. It implements the existing model, character, set, minimum-count
and Top/Worst filters while excluding deleted images.

`ArenaService.next_pair()` selects an unplayed directed pair from this canonical
pool. `record_decision()` accepts image UIDs; its repository stores the match
and both resulting rating events in one SQLite transaction. Existing URLs,
redirects and visible pairwise behavior remain compatible.

## 6. Curation and filesystem ownership

`CurationService.assign()` accepts a stable image UID. The repository resolves
the current PNG and optional sidecar path. `LocalCurationFileManager` performs a
reversible move without a database transaction being held; the repository then
updates the image paths and single assignment atomically. A failed database
write rolls the move back. Compensation failures are logged and returned as a
visible mutation failure.

A move changes path attributes only. Reviews, Arena matches and Curation facts
remain attached to the image UID, so no relinking cascade is required.

## 7. Canonical output catalog

`CanonicalOutputImageCatalog` implements the application
`OutputImageCatalog` and review-resolution ports. It obtains canonical rows
through `SqliteOutputImageRepository`, whose reader opens SQLite with
`mode=ro`. It validates current paths against the configured output root and
uses normalized canonical generation metadata. An optional sidecar path is
provenance and a filesystem attribute, not identity or required runtime input.

Runtime page reads do not recursively rediscover images and do not fall back to
the removed legacy scanner. Historical PNG/sidecar discovery is restricted to
the explicit offline import workflow.

## 8. Audited migration boundaries

### Historical output provenance

`legacy-output audit` scans PNGs and sidecars without changing them. Its report
binds the canonical database, source files and workflow graphs by hash.
`legacy-output import` revalidates that snapshot immediately before writing.
It preserves existing image/generation UIDs and protected generation fields,
creates content-derived identities for new outputs, and imports normalized
sampler stages. PNGs without sidecars are reported but not invented as new
canonical records.

### Legacy feature facts

`legacy-features audit` opens Ratings, Arena, Curation and supporting projection
sources read-only, binds each database by SHA-256 and resolves paths only as
migration evidence for an existing image UID. The importer writes ratings,
Arena matches and Curation assignments idempotently. Ambiguous mappings and
conflicts block the import; missing historical images and dependent facts are
reported as orphans rather than assigned path-derived identities.

Both importers create a canonical backup before the first write and use one
SQLite transaction. On a normal exception they roll back first and validate
the production database. Physical restore is conditional: it is used only
when validation fails, an out-of-transaction structural change occurred or
the commit state is uncertain. Restore failures are reported independently.
Reports, backups and runtime data are excluded from Git.

### Legacy Playground prompt catalog

`legacy-prompts audit` opens `playground.sqlite3` read-only and writes a
checksum-bound snapshot. `legacy-prompts import` revalidates the source and
canonical database hashes, creates a backup and imports every accepted item in
one transaction. Existing source IDs receive deterministic component UIDs;
prompt text becomes immutable revisions while name, tags and notes remain
mutable component metadata. Repeating the audit/import is idempotent and does
not remove unused catalog content.

The legacy Playground runtime has not yet been rewired to this catalog. Until
that later slice, it remains isolated rather than dual-writing both models.

## 8.1 Target generation boundaries

Generation is deliberately split into semantic and technical boundaries:

```text
GenerationRequest + WorkflowBlueprint
                  -> WorkflowCompiler
                  -> CompiledWorkflow
                  -> ComfyUiProvider
```

The blueprint repository loads versioned graph templates with explicit role and
expected output-node bindings. The compiler owns graph semantics and produces a
canonical graph hash, resolved roles and sampler stages. It transfers an
already-decided output policy into the graph but does not choose directories or
filenames. The ComfyUI provider only submits compiled graphs, tracks external
jobs, discovers capabilities and returns raw output descriptors.

Expected output bindings contain a role and node ID. Concrete batch/output
indices are assigned only when ComfyUI outputs are collected.

## 9. Schema lifecycle

Runtime startup validates supported canonical and transitional legacy schemas;
it never upgrades an unsupported database silently. Canonical v3 through v5
changes are available only through `python -m comfyreview canonical-db
upgrade` and are backed up. The v3-to-v4 step migrates writable legacy review
state into events, projects delete tombstones and replaces old tables with
read-only views; v5 adds the prompt catalog without changing those facts.

The older multi-file schema lifecycle remains centralized in
`comfyreview.repositories.sqlite.legacy_schema`. Its explicit
`legacy-db upgrade` command handles only known additive changes. This does not
claim crash atomicity across several SQLite files.

## 10. Remaining transitional boundaries

The canonical cutover is intentionally not the end of the wider refactor.

- ComfyUI generation still needs versioned blueprints, semantic compilation,
  a technical submit/wait/output provider and native multi-output collection.
- Playground selection/submission still uses legacy stores; the canonical
  prompt catalog exists but is not yet its runtime dependency.
- Prompt/statistics projections and their worker remain transitional.
- Frontend logic still needs the planned ES-module/API-client cleanup.

Existing projection workers are not migration targets by default. Each derived
dataset is first evaluated for replacement by a direct query or canonical SQL
view. A new idempotent worker is introduced only for a projection whose
materialization is demonstrably necessary.

Legacy sources may be read by explicit migration tools. They must not become a
second writable truth for an already cut-over feature.

## 11. Observability and quality

Request middleware validates or generates `X-Request-ID`, binds it through a
context variable, returns it on responses and emits structured JSON lifecycle
events without prompts, credentials or full local paths. Review, Arena,
Curation and migrations log state transitions and normalized failures.

Architecture tests enforce dependency direction, SQL placement and provider
ownership. New concrete core callables require manifest entries and behaviour
tests; the defined core scope retains 100% statement coverage. The complete
gate is `python scripts/quality.py`.
