# ComfyReview Refactor Plan

Status: canonical Review, Ranking, Arena and Curation cutover implemented on
`refactor/review-boundary`, 2026-09-30. The branch remains at review stop until
accepted and merged.

The goal is a maintainable local application with one canonical writable
database, stable identity and explicit providers. Behaviour and public routes
remain compatible unless a change is explicitly approved.

## Completed foundations

### Safety bridge

The initial safety work added output-root validation, reversible delete staging,
visible Arena/Curation failures, compensation and projection-worker recovery.
It protected the old multi-file runtime but never claimed cross-database crash
atomicity.

### Quality foundation

Merged through PR #4:

- pinned Ruff, mypy, Pyright, pytest and coverage tooling;
- deterministic `python scripts/quality.py`;
- versioned diagnostic and architecture ratchets;
- callable-to-test manifest and 100% statement coverage for the defined core;
- structured JSON logs and `X-Request-ID` propagation;
- Python 3.11/3.14 and Windows quality CI;
- documented default port 8000.

### Bootstrap and lifecycle

Merged through PR #5:

- typed side-effect-free settings;
- `ApplicationContainer` and `create_app()` composition root;
- explicit canonical and legacy schema lifecycles;
- class-owned worker runtime with bounded shutdown;
- compatible `app.py`, `main.py` and Uvicorn entry points;
- no implicit upgrade of unsupported existing databases.

## Implemented on the active cutover branch

### Audited historical output import

- separate read-only audit and write commands;
- report structure, canonical DB and source hashes revalidated before writes;
- existing 17 image/generation identities and protected fields preserved;
- 362 newly observed images/generations assigned content-derived identities;
- all 379 observed sampler stages imported from graph provenance;
- six observed PNGs without sidecars reported and not invented;
- source PNGs and sidecars left unchanged;
- backup-before-write, one transaction, rollback-first and conditional restore;
- canonical SQLite readers opened with `mode=ro`.

These counts describe the completed local migration run and remain control
observations rather than constants in the importer.

### Canonical schema v4

- append-only `review_events` is the only writable review truth;
- `images.deleted_at` is the rebuildable lifecycle projection;
- rating after delete atomically emits restore then rating;
- current-state and aggregate views derive from events;
- `image_reviews` and `deleted_images` are read-only compatibility views;
- `arena_matches` and `curation_assignments` reference canonical images;
- v3 to v4 is explicit, backed up and never performed by normal startup.

This is a deliberate product/data-model evolution from the legacy current-state
review table. The UI continues to show the current effective rating/delete
state while retaining the complete canonical event history.

### Audited legacy feature import

- Ratings, Arena and Curation sources opened read-only and SHA-bound to an audit;
- paths used only to resolve existing image UIDs;
- canonical v3 reviews deduplicated by idempotent source keys;
- ambiguous/conflicting mappings block the import;
- historical missing images and dependent facts reported as orphans;
- aggregate parity reported for review;
- all fact groups written idempotently in one canonical transaction;
- the live migration imported 5,454 legacy rating events, 1,224 Arena matches
  and 3 Curation assignments; unresolved facts remained reported, not invented.

The observed source totals of 14,907 ratings, 5,112 matches and 6 assignments
were validation controls, not hard-coded acceptance rules.

### Runtime identity cutover

- Review and Delete submit `image_uid`; current files and metadata resolve
  server-side;
- Top/Worst reads canonical aggregates, curation and lifecycle state;
- Arena selects and persists canonical UID pairs, with match and rating events
  committed atomically;
- Curation moves PNG plus optional sidecar outside a DB transaction, then
  updates path attributes and assignment atomically;
- DB failure after a move rolls the filesystem move back and exposes any
  compensation failure;
- sidecarless canonical images work in Review, Top/Worst, Arena, Curation and
  Delete;
- path-based Arena, Curation, pool and relinking runtime modules were removed;
- old Review/Arena/Curation databases receive no dual-writes;
- existing URLs, redirects and visible flows remain compatible.

## Current acceptance state

The active branch is the integration branch for the complete refactor. Pull
request #7 was closed without merge so later slices can continue as small,
pushed commits on the same branch. A new pull request is opened only after the
complete architecture, regression and documentation acceptance.

Runtime imports and their reports/backups are deliberately outside Git.

## Completed continuation slices

### A. Rules and targeted quality feedback

- repository rules now name the compiler/provider/output-policy boundaries;
- the callable manifest covers stable public Core behavior rather than private
  implementation details;
- `scripts/quality.py --targeted --test <node>` checks changed Python files and
  always includes architecture and manifest contracts;
- targeted mode is documented and implemented only as feedback; the full gate
  remains the slice acceptance criterion.

### B. Canonical identity consolidation

- Review and Delete application commands now accept only canonical
  `image_uid` identity;
- legacy hidden path form fields remain accepted by HTTP routes but are ignored;
- the canonical resolver derives paths and metadata exclusively server-side;
- path-derived image and generation UID fallbacks were removed;
- the unreferenced sidecar-scanning `LocalOutputImageCatalog` and its obsolete
  tests were removed;
- canonical runtime readers remain SQLite `mode=ro`, while schema v4
  compatibility views remain read-only.

## Remaining slice order

The dependency order is binding. In particular, Playground does not receive a
temporary generation facade and the ComfyUI provider never owns workflow
semantics.

1. simplify Review, Ranking, Arena and Curation boundaries;
2. migrate the complete prompt catalog with immutable revisions;
3. move Playground selection and rendering behind catalog/policy boundaries,
   while leaving legacy submission isolated;
4. evaluate every legacy projection as direct query, SQL view, materialization
   or deletion;
5. remove remaining multi-database runtime dependencies;
6. introduce versioned `WorkflowBlueprint` and the semantic
   `WorkflowCompiler`;
7. introduce the technical `ComfyUiProvider` for compiled graphs only;
8. implement `GenerationService` and its canonical asynchronous lifecycle;
9. collect native multi-output results and assign real output indices only
    from returned ComfyUI outputs;
10. apply explicit output policy and migrate to standard `SaveImage`;
11. wire Playground to the real generation port and delete obsolete legacy
    clients, stores, workers and compatibility paths;
12. migrate browser behavior to ES modules and the shared API client;
13. run the complete architecture, data, browser, quality and documentation
    acceptance before opening a new pull request.

Each intermediate commit runs focused tests and static checks for changed
files. The targeted command is feedback only. Every completed slice and the
final integration require a successful full `python scripts/quality.py` run.

## Invariants for remaining work

- one writable authority for each fact; no durable dual-writes;
- stable IDs, never paths, are relational identity;
- SQL stays in repositories or explicit offline migration adapters;
- external filesystem/API work does not run inside SQLite write transactions;
- schema changes are explicit, versioned and backed up;
- every stable public core behavior boundary has an explicit behaviour test
  and manifest entry;
- private implementation details are tested through their public owner or
  extracted when they contain independent domain policy;
- affected tests pass before each commit and the complete quality gate passes
  at every slice boundary and before integration;
- documentation describes implemented state and labels targets as targets.

## Non-goals

- a SPA rewrite;
- cloud or multi-user deployment;
- Character Chronicles gameplay;
- copying rebuildable legacy aggregate tables unchanged;
- preserving obsolete path-based runtime architecture for compatibility.
