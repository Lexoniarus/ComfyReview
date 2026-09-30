# ComfyReview Refactor Plan

Status: active canonical review and identity migration; audited historical
output import implemented, 2026-09-30.

Goal: bring ComfyReview to the same engineering standard as the current
World Freight Idle codebase before using it as the data/application foundation
for further Character Chronicles work.

The refactor must preserve working ComfyReview behavior while replacing
architectural debt deliberately.

## Safety bridge before Phase 1

The first implementation milestone hardens legacy mutations without changing
the physical database layout:

- validate output pairs below the configured ComfyUI output root
- stage deletes reversibly before recording their review tombstone
- reject invalid Review, Arena and Curation commands explicitly
- compensate ordinary partial Arena/Curation failures where possible
- fail projection jobs on rebuild errors and recover abandoned worker jobs at
  startup

Cross-database crash atomicity remains deferred to the canonical database. The
safety bridge must not be represented as a replacement for the future Unit of
Work.

## Phase 0 – Baseline documentation

Deliverables:

- `AGENTS.md`
- `docs/CODING_STANDARDS.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_ARCHITECTURE.md`
- this plan

Exit condition:

- rules are in the repository and treated as binding for new/changed code

## Phase 1 – Quality foundation

Status: merged into `master` through PR #4.

Introduce without changing product behavior:

- `pyproject.toml` project rules
- Ruff lint/format
- mypy
- Pyright
- coverage configuration
- `tests/function_test_manifest.py`
- architecture tests
- `scripts/quality.py`
- structured logging foundation + trace ID helper

Define the exact Python-core coverage scope during this phase.

Implemented details:

- pinned development tools in `requirements-dev.txt`
- a versioned file/diagnostic ratchet that cannot grow
- AST architecture checks with explicit legacy exceptions
- a callable-to-test manifest and 100% statement coverage for the current core
- structured JSON logging and HTTP `X-Request-ID` propagation
- Python 3.11/3.14 quality CI plus a Windows 3.14 regression job
- public default port aligned to `8000`; local environment overrides remain
  supported

Exit condition:

- one repeatable quality command exists
- current violations are measured rather than hidden
- no new code may worsen the baseline

## Phase 2 – Package and dependency boundaries

Status: bootstrap foundation merged through PR #5. The first feature slice,
`refactor/output-image-boundary`, is implemented and awaiting review. Remaining
feature slices are pending.

Implemented bootstrap foundation:

- `comfyreview/` package with typed, side-effect-free settings
- application lifecycle ports for legacy schemas and the worker runtime
- central SQLite legacy-schema adapter and schema-free normal repository opens
- read-only startup validation and temporary initialization of missing files
- explicit `legacy-db validate` and backed-up additive `legacy-db upgrade` CLI
- class-owned worker thread with injected paths/debounce and bounded shutdown
- `ApplicationContainer` and `create_app()` FastAPI composition root
- lifespan ownership of directories, schema startup and worker start/stop
- observability moved into `comfyreview/` without a compatibility wrapper
- compatible root `app.py`, `main.py`, `python main.py` and `uvicorn app:app`

The current bootstrap still wires legacy routers and feature implementations.
Review, output-image, Arena, curation, ComfyUI generation, prompt/playground and
projection boundaries move one vertical slice at a time after this milestone.

Implemented output-image read slice:

- application-layer `OutputImageCatalog` port and `OutputImageReadModel`
- class-owned `LocalOutputImageCatalog` with injected output root
- recursive PNG/sidecar discovery and legacy metadata normalization behind the
  provider boundary
- resolved output-root containment and exclusion of internal trash/export
  directories
- explicit catalog injection into Review, Top, Arena GET and Arena POST reads
- removal of the parallel legacy `scanner.py` implementation
- architecture checks against direct concrete-provider and legacy-scanner
  imports in routes/services

This slice is read-only. Paths remain compatibility attributes rather than
stable image identity. Delete/trash, curation moves, path relinking and browser
URL mapping remain legacy behavior for their later vertical slices. No database
schema, migration, persisted `image_id` or dual-write behavior was introduced.

Implemented historical output import:

- explicit audit snapshot followed by a separate write command
- immediate PNG, sidecar and workflow-hash revalidation before writes
- preservation of existing image/generation identities, lifecycle fields and
  occupied output slots
- content-derived identities for newly imported images and generations
- normalized graph provenance and every standard sampler stage
- backup emission before writes and one canonical SQLite transaction
- rollback-first recovery with conditional backup restore
- read-only canonical image queries through SQLite `mode=ro`

This importer deliberately does not migrate historical ratings, Arena matches
or curation assignments. Those facts belong to the schema-v4 feature cutover,
where canonical image IDs replace path identity without dual-writes.

Create the target `comfyreview/` structure and composition root. The package
name avoids a conflict with the compatible root `app.py` entry point.

Move behavior incrementally behind:

- domain models/ports
- application services
- repositories
- providers
- API routes

Initial high-value seams:

1. image read model and output discovery (implemented, awaiting review)
2. review/rating persistence and delete/trash filesystem mutations
3. Arena persistence
4. curation persistence and reversible filesystem moves
5. ComfyUI client
6. prompt/playground persistence
7. MV/background worker

Rules:

- behavior-preserving refactor first
- SQL leaves services/routes
- ComfyUI/filesystem access leaves services/routes
- concrete config paths stop leaking into business services

Exit condition:

- application use cases can be tested with injected fake repositories/providers
- architecture tests enforce the boundaries

## Phase 3 – Canonical ComfyReview database design

Finalize the vNext schema based on `docs/DATA_ARCHITECTURE.md`.

Required design topics:

- stable image identity
- normalized prompt/component/composition identity
- exact prompt + atom membership model
- review events
- Arena relations
- curation relations
- raw ComfyUI metadata provenance
- derived statistics strategy
- job/projection state
- schema versioning
- indexes and foreign keys

Do not implement a giant migration until the schema review is accepted.

Exit condition:

- schema and invariants documented
- migration mapping from every legacy DB is explicit

## Phase 4 – Offline migration tool

Build an explicit offline importer from legacy databases into a NEW canonical
SQLite file.

Inputs may include:

- `playground.sqlite3`
- `ratings.sqlite3`
- `arena.sqlite3`
- `curation.sqlite3`
- other legacy aggregate DBs for verification only

Do not blindly copy rebuildable databases:

- `prompt_tokens.sqlite3`
- `images.sqlite3`
- `prompt_ratings.sqlite3`
- `combo_prompts.sqlite3`
- `mv_jobs.sqlite3`

Instead rebuild their required semantics from canonical facts unless a review
identifies non-derivable information that must be preserved.

Migration report must include:

- source fingerprints/paths
- row counts
- migrated/ignored categories
- relationship validation
- orphan detection
- aggregate parity checks
- integrity check
- output schema version

Exit condition:

- repeatable migration on copies
- no source files modified
- validation report accepted

## Phase 5 – Runtime cutover

Switch repositories from the legacy multi-DB paths to the canonical database.

Rules:

- one runtime persistence path
- no dual writes
- legacy readers allowed only in explicit offline import tools
- rollback is switching back to the untouched old runtime/data, not trying to
  reverse a destructive in-place migration

Exit condition:

- ComfyReview feature regression passes against canonical DB
- legacy DBs are no longer required by normal startup

## Phase 6 – Frontend cleanup

Without a SPA rewrite:

- extract inline request logic into native ES modules
- centralize API access
- eliminate new dynamic `innerHTML`
- define component lifecycle for stateful UI
- add frontend lint/format/checkJs gates

Exit condition:

- templates render
- modules interact
- requests are centralized
- frontend quality gate is green

## Phase 7 – Remove/refine derived projections

Measure real query performance on the canonical schema.

Only then decide which projections need materialization.

Likely sequence:

1. normal SQL views
2. indexes
3. query improvements
4. materialized/rebuildable tables only where measured necessary

Avoid recreating the old pattern of large eager Cartesian projections.

## Phase 8 – Character Chronicles integration decision

Only after ComfyReview vNext is stable:

Decide whether Character Chronicles:

- imports the same domain package but uses its own database, or
- extends the same physical SQLite database with explicit CC-owned tables

Evaluate separately:

- image description worker
- embeddings/RAG
- gameplay state
- campaign/quest/card systems

Do not let future Character Chronicles requirements distort the ComfyReview
core before those requirements are explicit.

## Non-goals of the initial refactor

- rewriting the application as a SPA
- changing every UI screen at once
- adding cloud deployment
- adding multi-user support
- adding Character Chronicles gameplay
- copying all historical aggregate tables into a new database unchanged
- preserving accidental legacy architecture merely for compatibility
