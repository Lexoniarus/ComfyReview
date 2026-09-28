# ComfyReview Refactor Plan

Status: planning baseline, 2026-09-28.

Goal: bring ComfyReview to the same engineering standard as the current
World Freight Idle codebase before using it as the data/application foundation
for further Character Chronicles work.

The refactor must preserve working ComfyReview behavior while replacing
architectural debt deliberately.

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

Exit condition:

- one repeatable quality command exists
- current violations are measured rather than hidden
- no new code may worsen the baseline

## Phase 2 – Package and dependency boundaries

Create the target `app/` structure and composition root.

Move behavior incrementally behind:

- domain models/ports
- application services
- repositories
- providers
- API routes

Initial high-value seams:

1. review/rating persistence
2. image read model
3. ComfyUI client
4. output scanner/filesystem
5. Arena persistence
6. curation persistence
7. prompt/playground persistence
8. MV/background worker

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
