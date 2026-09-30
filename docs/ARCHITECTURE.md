# ComfyReview Architecture

Status: active migration with canonical image reads and audited output import
implemented, 2026-09-29.

The current public prototype is functional but still predates many of these
boundaries. The typed settings, lifecycle ports, central legacy-schema adapter,
owned worker runtime, FastAPI composition root and read-only output-image
catalog described below are now implemented. Other feature-specific services
and ports remain target architecture until their vertical slices are migrated.

## 1. Product boundary

ComfyReview is a local-first application for:

- discovering ComfyUI image outputs and metadata
- reviewing and rating generated images
- pairwise Arena comparisons
- curation and set assignment
- prompt/content management
- statistical learning from review history
- reproducible handoff back to ComfyUI

Character Chronicles may later reuse or extend this domain, but Character
Chronicles gameplay, image description workers and embedding/RAG systems are not
part of the ComfyReview core refactor unless explicitly added as product scope.

## 2. Target layers

```text
Browser / Jinja
      |
      v
FastAPI API + page routes
      |
      v
Application services
      |
      v
Domain ports / typed domain values
   |                 |
   v                 v
Repositories       Providers
(SQLite)           (ComfyUI / filesystem)
```

Concrete assembly occurs in one composition root.

The current `comfyreview.bootstrap.create_app()` constructs an
`ApplicationContainer` with typed settings, a `LegacySchemaLifecycle` adapter,
a `WorkerRuntime` and an `OutputImageCatalog`. Its FastAPI lifespan owns
directory preparation, schema startup validation, worker start and bounded
worker stop. The container is available to HTTP routes through application
state. Root `app.py` and `main.py` remain compatibility entry points.

Target package shape (introduced incrementally after the quality foundation):

```text
comfyreview/
  domain/
    models.py
    values.py
    ports.py
    policies.py
  services/
    review.py
    arena.py
    curation.py
    generation.py
    prompt_learning.py
    ingestion.py
  repositories/
    sqlite/
      connection.py
      images.py
      reviews.py
      prompts.py
      compositions.py
      arena.py
      curation.py
      jobs.py
  providers/
    comfyui.py
    output_images.py
  api/
    routes/
    projections.py
  workers/
    runtime.py
  bootstrap.py
  main.py
```

The exact file split may change, but the dependency direction does not.

## 3. Domain model direction

The core domain should speak in stable concepts, not database filenames.

Primary concepts:

- `PromptComponent` – character, scene, outfit, pose, expression, modifier,
  lighting or another reusable prompt/content component.
- `PromptComposition` – a concrete ordered set of components used or prepared
  for generation.
- `Prompt` – exact positive/negative prompt text with stable identity.
- `PromptAtom` – normalized/reusable atom derived from a prompt.
- `ImageRecord` – one generated image with stable ID and generation metadata.
- `ReviewEvent` – user rating/delete/restore judgment about an image.
- `ArenaMatch` – pairwise comparison between two image IDs.
- `CurationAssignment` – optional dataset/set assignment for an image.
- `BackgroundJob` – operational work item such as aggregate refresh/import.

Derived statistical concepts may exist but are not canonical facts.

## 4. Canonical runtime database

The target ComfyReview runtime uses one writable SQLite database.

Legacy databases remain readable migration sources during transition:

```text
ratings.sqlite3
prompt_tokens.sqlite3
images.sqlite3
prompt_ratings.sqlite3
combo_prompts.sqlite3
playground.sqlite3
arena.sqlite3
curation.sqlite3
mv_jobs.sqlite3
```

The old file split is not preserved as a runtime architectural requirement.

### Canonical facts

The new database should contain normalized source-of-truth records for:

- prompt/content components
- prompt compositions and membership
- exact prompts and atom membership
- images and generation metadata
- review events
- arena comparisons
- curation assignments
- operational jobs/schema metadata

### Derived/rebuildable state

Examples:

- image score aggregates
- prompt atom statistics
- composition statistics
- ranking projections

Cheap aggregates should begin as SQL views. Materialization is introduced only
when measured performance requires it.

## 5. Identity model

File paths are not domain identity.

Target rule:

```text
stable image_id / image_uid
        |
        +-- generation_id -> GenerationRun
        +-- output_node_id / output_index
        +-- current png_path
        +-- optional legacy json_path
        +-- reviews
        +-- arena matches
        +-- curation
```

Moving a PNG/JSON pair must not require relinking every dependent table.

The ComfyUI metadata export boundary should eventually provide or allow creation
of a stable generation/image identifier.

## 6. Prompt learning model

The legacy prompt-token pipeline duplicates atom text per rating/run. The target
model separates prompt structure from review events:

```text
Prompt
  |
  +-- PromptMembership -- PromptAtom
  |
  +-- ImageRecord -- ReviewEvent
```

A prompt is tokenized once. Ratings remain attached to images/review events.
Prompt-atom performance is derived through joins and may be cached in a small
aggregate table.

This preserves the learning semantics without requiring a very large
per-rating token journal as the canonical source of truth.

## 7. Prompt compositions

Legacy `combo_prompts` eagerly expands large portions of the theoretical
character x scene x outfit space.

Target rule:

- components are canonical reusable records
- a composition stores membership relationships
- persist compositions that are generated, used, curated or intentionally
  prepared
- do not precompute every possible combination by default

This keeps the domain relational without storing a large Cartesian product.

## 8. ComfyUI boundary

ComfyUI is an injected provider.

A generation use case should conceptually look like:

```text
GenerationService
  -> prepare generation request from domain data
  -> ComfyUiProvider.submit(...)
  -> receive external job/prompt ID
  -> poll/watch outside DB write transaction
  -> ComfyUiProvider.fetch_outputs(...)
  -> persist resulting image facts atomically
```

Long-running work is explicit. A timeout while waiting does not imply the
ComfyUI job failed.

The provider owns HTTP/API details and workflow patching. Services own product
intent.

## 9. Filesystem boundary

ComfyUI output scanning and sidecar parsing are external-input concerns.

The read-only part of this boundary is implemented. The application-layer
`OutputImageCatalog` port returns typed `OutputImageReadModel` values. The
composition root injects `LocalOutputImageCatalog`, which owns recursive PNG
discovery, matching JSON-sidecar reads, output-root containment checks and the
legacy checkpoint/model/combo metadata fallbacks. Missing sidecars are skipped;
invalid or unreadable sidecars remain visible with empty metadata, preserving
the established page behavior. Review, Top and Arena reads use this port and no
longer import the deleted legacy `scanner.py` module.

`png_path` and `json_path` in this read model are compatibility attributes,
not stable identity. This slice intentionally does not introduce `image_id`,
database persistence, data migration or dual writes.

Physical file moves for trash/curation/export are explicit provider operations
coordinated by a service. Persistence updates are committed only after the
filesystem operation has a known outcome.

Those mutating operations have not yet moved to the new provider architecture.
Delete/trash still uses `OutputFileService`, curation retains its legacy move
and path-update flow, and browser URL mapping remains in
`services/file_urls.py`. Each moves in its corresponding later vertical slice.

## 10. Transactions

- Repositories participate in an explicit Unit of Work for related mutations.
- Review write + related canonical state changes commit together.
- External ComfyUI execution occurs outside write transactions.
- Filesystem/network work does not run while holding a long SQLite write lock.
- After an external action, mutable state is revalidated before final commit
  when correctness depends on it.

### Legacy safety bridge

Until the canonical database cutover, a few workflows still span independent
SQLite files and the ComfyUI output filesystem. The legacy runtime therefore
uses explicit validation and compensating actions:

- submitted PNG/JSON paths must resolve to an existing matching pair below the
  configured output root
- delete operations stage the pair in the configured trash location before the
  review tombstone is written and restore it if that write fails
- Arena and curation workflows surface failures and compensate completed legacy
  writes or file moves where possible
- projection failures fail their queue job; startup marks jobs abandoned by a
  previous process as failed and schedules one catchup when projections lag

These measures protect ordinary failure paths but do not claim crash atomicity
across multiple SQLite files. That guarantee requires the later canonical
database and Unit of Work.

## 11. Workers and derived projections

Background workers are application infrastructure, not a second business-logic
path.

Workers call the same services/repositories used by synchronous workflows.
They may maintain derived projections, but every projection must document:

- its source facts
- its rebuild procedure
- its freshness marker
- failure behavior

Worker queues and projection cursors may live in the same canonical database.

## 12. API and frontend

FastAPI routes translate HTTP and render Jinja responses or JSON projections.
They call services rather than stores/providers directly.

Jinja remains acceptable. New interactive browser behavior should move into
native ES modules with a shared API client and explicit lifecycle where stateful.

## 13. Observability

Externally visible workflows use structured events and trace IDs.

The current foundation provides a standard-library JSON formatter and ASGI
request middleware in `comfyreview/observability.py`. For HTTP requests it:

- accepts a safe caller-provided `X-Request-ID` or generates a UUID
- returns the effective ID in the response, including controlled errors
- binds the ID through a context variable for downstream logs
- resets context after success or failure
- records stable request lifecycle events without arbitrary prompt payloads

The composition root installs this middleware for every application instance.

Minimum workflows:

- review save/delete/restore
- Arena decision
- ComfyUI generation submit/complete/fail
- ingestion scan/import
- projection rebuild
- migration

Logs describe IDs and outcomes rather than dumping full private payloads.

## 14. Enforced architecture boundary

AST-based tests now measure existing boundary violations and reject new ones.
The current legacy exceptions are versioned in
`quality/architecture_baseline.json`. Future modules below
`comfyreview/domain` and `comfyreview/application` have no legacy exceptions;
they may not import SQLite, FastAPI, global configuration, routes, stores or
legacy services into the core.

Routes and legacy services are additionally prevented from importing concrete
`comfyreview.providers` implementations or reviving the removed legacy output
scanner. Only bootstrap wiring knows the local output-image provider.

## 15. Migration posture

### Implemented pre-One-DB bootstrap boundary

Legacy schema ownership now lives only in
`comfyreview.repositories.sqlite.legacy_schema`. Normal store calls open an
existing database in SQLite `rw` mode and cannot create database files or run
schema DDL. Startup first validates every existing configured database
read-only. It initializes only files that do not exist at all; an existing
empty, corrupt, old, or incompatible file aborts startup.

Known additive upgrades are available only through
`python -m comfyreview legacy-db upgrade`. The command backs up every affected
existing file before the first mutation, validates the result, and restores the
backups after an ordinary failure. Validation is available through the sibling
`validate` command.

The legacy worker is now a class-owned runtime with injected paths, debounce
and stop event. It prevents concurrent double-starts and reports a bounded
shutdown timeout. Projection behavior is still legacy-compatible and will move
behind feature-specific services in a later slice.

This boundary does not provide crash atomicity across multiple SQLite files.
That remains impossible until the canonical one-database cutover.

### Implemented output-image read boundary

Output discovery is now a replaceable, read-only provider behind an
application port. The page-read services consume an injected catalog, while
routes obtain the configured instance from `ApplicationContainer`. This is the
first feature-specific vertical boundary and deliberately stops before review,
Arena or curation mutation ownership.

Canonical image queries use a genuine SQLite read-only connection. Historical
PNG/sidecar provenance enters the canonical database only through the explicit
offline `legacy-output` audit/import workflow. The audit binds a snapshot to
content hashes; the importer revalidates that evidence before creating or
enriching stable identities. It creates a backup before the single write
transaction and never changes source PNGs or sidecars.

The output importer owns generation provenance only. Historical review, Arena
and curation facts remain separate migration inputs for the schema-v4 cutover;
there is no transitional dual-write between legacy and canonical stores.

Refactor and data migration are staged:

1. establish engineering rules and quality gate
2. introduce ports/repositories/providers around existing behavior
3. define canonical schema and importers
4. migrate copies of legacy data and verify invariants
5. switch application runtime to the canonical database
6. remove legacy runtime paths only after acceptance

The old databases remain untouched until a migration result has been validated.
