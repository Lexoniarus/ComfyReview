# ComfyReview Refactor Plan

Status: the canonical backend cutover, structured prompt catalog, schema-v7
data migration and the first Frontend V2 surfaces are implemented on
`refactor/review-boundary`, 2026-10-02. The remaining Frontend V2 overhaul is
functional work rather than final polish: bounded Analytics collections,
Playground handoffs, generation profiles and LoRA stacks, the complete Settings
surface, Inspector composition and browser acceptance remain. The branch stays
unmerged until the full refactor is accepted.

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

### C. Review, Ranking, Arena and Curation boundaries

- Review persistence now resolves an existing canonical image/generation pair
  and never creates or rewrites provenance during a review;
- legacy PromptProjection writes and impossible append-only compensation were
  removed from `ReviewService`;
- Ranking, Arena and Curation SQLite adapters now live in separate
  responsibility-focused repository modules;
- legacy projection repositories are isolated from canonical review-event
  persistence pending the explicit projection audit;
- routes retain their existing URLs, fields and redirects while passing stable
  UIDs into application services.

### D. Revisioned prompt catalog

- canonical schema v5 adds stable prompt components, immutable revisions and
  reproducible compositions without materializing a Cartesian product;
- `PromptCatalogService` owns creation, revision, mutable metadata,
  archive/restore and listing behavior through an injected repository;
- unused authored catalog content is retained;
- `legacy-prompts audit` reads the legacy Playground source in read-only mode
  and binds it plus the canonical database to a checksum-protected report;
- `legacy-prompts import` revalidates that report, creates a backup and writes
  the accepted catalog idempotently in one transaction;
- Playground submission uses the native GenerationService; there is no
  temporary generation facade and no dual-write.

### E. Playground preparation boundary

- `PromptSelectionPolicy` owns deterministic manual/random selection and
  compatibility rules over canonical catalog components;
- `PromptRenderer` produces exact positive/negative snapshots plus the used
  immutable revision UIDs;
- `PlaygroundService` composes catalog reads, selection and rendering without
  submitting external work;
- `GenerationPort` is implemented by the canonical `GenerationService`;
- preview drafts now use canonical revisions while preserving their existing
  persisted UI shape and legacy numeric form inputs during transition;
- draft overrides remain non-persisting snapshots and never rewrite catalog
  revisions;
- the obsolete `PlaygroundGenerator` facade and its helper modules were
  removed;
- native submission, lifecycle tracking and output collection are wired.

### F. Legacy projection audit

The usage audit is recorded in `docs/PROJECTION_AUDIT.md`. Image ranking,
prompt performance, prompt-token statistics, combo statistics,
recommendations and best-image lookup can all be replaced by canonical
repository queries with bounded deterministic aggregation. No replacement
materialized worker is currently justified. `mv_jobs` and `mv_state` therefore
remain historical offline evidence only; the runtime worker and its consumers
have been removed.

### Slice 0. Canonical Data Completion (completed)

- the explicit `legacy-compositions audit/import` workflow is implemented;
- audit format v2 recognizes complete positive/negative prompt-atom blocks in
  variable, ordered slot sets rather than requiring all seven catalog kinds;
- unique memberships are imported even when the immutable generation snapshot
  contains additional historical draft text; that text never creates a
  synthetic component or revision;
- ambiguous and missing evidence remain diagnostics rather than guessed data;
- every import is hash-bound, backed up, idempotent and transactional;
- the full rehearsal on a v4 database copy successfully upgraded to v6 and
  reran Output, Prompt, Feature and Composition imports idempotently;
- the live v6 database contains 379 stable generations/images and sampler
  stages, verified content hashes for all images, 729 components and immutable
  revisions, 275 compositions and 1,280 composition memberships;
- 363 generations are linked: 29 exact render roundtrips and 334 memberships
  with preserved historical draft overrides;
- 16 generations remain intentionally unlinked: two ambiguous and fourteen
  without sufficient catalog evidence; no conflicts were observed;
- final integrity, foreign-key, identity, protected-field, provenance,
  read-only-reader and canonical-only startup checks passed.

Detailed reports and all four pre-write backups remain ignored runtime
artifacts. The counts above are observed migration results, not importer
constants.

### Frontend V2 analytics correction (completed)

- the live canonical output import was rerun idempotently and all 379
  generations now expose their normalized checkpoint without an `unknown`
  fallback;
- parameter summary distinguishes marginal calculated recommendations from
  actually observed full render setups;
- Checkpoint, Steps, CFG, Sampler and Scheduler are independent server-loaded
  views, and changing views cancels the prior request;
- observed setups are built from canonical generation and ordered sampler-stage
  facts, never from browser parsing of `combo_key`;
- prompt combinations and render setups are separate views, with a focused
  per-composition render-setup endpoint;
- example images remain bounded and lazy-loaded;
- static ES modules require revalidation, and the corrected Analytics module
  graph has a new stable filename to invalidate the previously cached graph;
- the completed slice passed the full Python/frontend quality gate and browser
  checks at desktop and 1180 x 820 without console errors or horizontal
  overflow.

### Structured prompt bundles and schema v7 (completed)

- `PromptRevision` now owns ordered positive and negative `PromptAtomUsage`
  values with text and `weight_milli` stored separately;
- schema v7 adds `prompt_revision_atom_usages` without changing stable
  component, revision, composition, generation or image identities;
- the explicit v6-to-v7 migration was rehearsed, backed up and applied to the
  stopped live database; 729 revisions produced 4,061 validated usages;
- Catalog V2 authoring and Playground drafts accept atom arrays only, while
  rendered prompt columns remain immutable derived snapshots;
- preview and generation submission share the server-side `PromptRenderer`;
- draft edits, reordering and reset operate on copies and never mutate the
  selected immutable revision;
- the legacy HTML form adapter is the only normal compatibility boundary that
  parses combined prompt text;
- the live database validates as schema v7 with `integrity_check = ok` and no
  foreign-key violations.

## Remaining slice order

The dependency order is binding. In particular, Playground does not receive a
temporary generation facade and the ComfyUI provider never owns workflow
semantics.

1. paginate and encapsulate Analytics collections and evidence cards;
2. add explicit Analytics-to-Playground intents without automatic submission;
3. introduce schema v8, generation profiles and normalized LoRA selections;
4. compile explicit ordered LoRA stacks through a versioned workflow blueprint;
5. add the complete Settings surface and read-only runtime diagnostics;
6. finish Inspector composition, responsive/accessibility behavior and remove
   replaced presentation paths;
7. finish the usage audit and delete only proven-dead compatibility code;
8. run the complete architecture, data, browser, ComfyUI, quality and
   documentation acceptance before opening a new pull request.

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
