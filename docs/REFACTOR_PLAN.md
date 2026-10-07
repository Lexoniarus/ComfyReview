# ComfyReview Refactor Plan

Status: the canonical backend cutover, structured prompt catalog, schema-v14
data migration and Frontend V2 overhaul are implemented on
`feature/lora-catalog-handoff`, 2026-10-07. Analytics collections are bounded,
Playground handoffs are explicit, generation profiles are dormant migration
compatibility, Settings is a complete product surface, the Inspector is
composed from focused views and Playwright covers the browser acceptance
contract. The branch stays unmerged until final user acceptance and the final
integration review.

The Anime-upscale/content-correction feature slice is implemented separately
from the refactor history and must be cleanly rebased with concurrent
Frontend-V2 work before integration.

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
- Review candidate selection now interprets the compatibility preference as
  “unrated first”, then falls back to the oldest review sequence; rated images
  are never permanently excluded by that preference;
- `FairArenaPairingPolicy` derives cooldown rotation from canonical match
  history, keeps repeated reads stable and delays reverse directions until
  older eligible images have rotated;
- the ineffective public `review_max_attempts` setting has been removed while
  its schema column remains dormant compatibility.

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
- draft responses and generation requests exchange ordered typed
  component/revision bindings, so confirmation preserves historical revisions
  and accepts an explicitly bound archived revision without restoring it to
  active/random selection;
- draft overrides remain non-persisting snapshots and never rewrite catalog
  revisions;
- the obsolete `PlaygroundGenerator` facade and its helper modules were
  removed;
- native submission, lifecycle tracking and output collection are wired.
- one FastAPI-lifespan-owned worker now observes bounded submitted/running work,
  recovers interrupted local states without resubmission and shuts down through
  a single owned thread lifecycle;
- explicit reconciliation can recover one strictly unambiguous persisted PNG
  through the normal canonical collector when ComfyUI history has expired.

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

### Legacy prompt provenance completion (completed)

- `legacy-provenance audit` reads the canonical database without mutation and
  distinguishes embedded recipes, unique exact matches and reviewed semantic
  reconstruction;
- the reviewed curation manifest records only this workspace's historical
  evidence and is not imported into normal runtime behavior;
- `legacy-provenance recover` can only create a separate output database and
  validates it before publication;
- historical variants are immutable lower-numbered revisions; the pre-existing
  current revision remains unchanged and latest;
- one-off recovered components are archived, while original rendered prompts,
  images, reviews, Arena matches and content classifications remain unchanged;
- the 2026-10-05 rehearsal covered 385 generations, created 109 missing
  historical revisions, relinked 324 generations and left all 377 active-image
  generations with a character membership and no ambiguous slot.

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
- this slice concluded with a valid schema-v7 database; the later explicit
  schema-v8 Settings/Profile upgrade is recorded below.

### Frontend V2 overhaul and schema v9 (completed)

- Analytics collections use deterministic pagination, one lifecycle-owned
  collection controller, stale-request cancellation and bounded lazy image
  evidence;
- Analytics, example-image and top-combination handoffs serialize a typed
  Playground intent and never create or submit a draft automatically;
- schema v8 adds typed workspace preferences, generation profiles, ordered
  profile LoRAs and normalized LoRAs actually used by generations;
- schema v9 adds cumulative workspace content levels and explicit profile/
  generation canvas dimensions; the upgrade was rehearsed, backed up and
  applied to the stopped live database without changing the 379 stable image
  or generation identities;
- one shared SQLite content predicate gates Top/Worst, Review, Arena, Scopes,
  Analytics and evidence lists from canonical component tags; browser filters,
  paths and prompt heuristics are not alternative policy implementations;
- Playground selection applies the same content policy before draft creation
  and again when exact revision/composition handoffs are restored;
- Blueprint v3 maps explicit canvas width/height roles; the compiler validates
  dimensions while the ComfyUI provider remains graph-semantic-free;
- Blueprint v2 exposes an explicit LoRA insertion role and the compiler builds
  a deterministic Model/CLIP loader chain without provider-side graph logic;
- `/settings` owns General, Content levels/LoRAs, Review, Curation, ComfyUI and
  Storage/database sections; environment configuration stays read-only;
- the Inspector delegates Context, Prompt, Generation, Workflow, Reviews and
  Curation rendering to focused views;
- Scope navigation renders only the active kind instead of hundreds of buttons
  at once;
- Playground top combinations use independently ranked Top-2/Top-3 rows per
  character and cyclic arrow/touch-controlled evidence rails; native
  scrollbars are hidden and one to three images fill a bounded card;
- Playwright runs against a temporary schema-v11 database and fake ComfyUI and
  covers bounded Analytics, Settings persistence, the Playground carousel and
  the four required viewport sizes;
- Node 24, ESLint, Prettier, Stylelint, checkJs, Vitest coverage and Playwright
  are part of `python scripts/quality.py` and CI.

### Anime upscaling and correctable content levels (completed feature slice)

- schema v10 adds output tiers/target geometry, canonical LoRA definitions,
  immutable generation-level LoRA snapshots, inferred content level and
  append-only image override events plus projection;
- Blueprint v4 owns the fixed AnimeSharp/sharpen/Lanczos output path and maps
  only semantic target geometry roles; capability validation blocks missing
  nodes or `example-upscaler.pth` before persistence/submission;
- Settings creates classified LoRA trigger revisions and offers explicit,
  revision-checked preview/apply commands for historical reclassification;
- unclassified LoRAs cannot be added to a Playground request;
- Top/Worst can raise, lower or inherit an image level and reuses the existing
  confirmation plus UID-based delete API;
- shared repository visibility uses the same effective-level policy across all
  image-bearing surfaces; Card Battler and card development remain outside
  this feature slice.

### Playground and geometry refactor completion (completed feature slice)

- `/playground` is the Top-2/Top-3 overview, `/playground/generator` is the
  explicit generator, and `/generations` is lifecycle history;
- one server-materialized seed drives selection and the base sampler; draft
  UIDs no longer depend on secure-context browser APIs;
- direct generation controls replace active profiles, while grouped atom
  overrides and prompt/sampler evidence share the authoritative renderer and
  central content visibility;
- schema v11 adds only rebuildable image geometry, refreshed by an explicit
  PNG-header scan and atomic replacement;
- Analytics and Inspector expose actual/classified geometry, and Playwright
  covers cyclic carousels, four viewports and an insecure LAN-style origin.

### Evidence-guided Generator and focused Analytics (completed feature slice)

- `RenderGuidanceService` replaces the active additive recommendation path for
  both Generator and Render Analytics without a schema change;
- observed setup, observed parameter, predicted setup and predicted parameter
  modes share immutable event evidence, independent-image support thresholds,
  deterministic ranking, shrunk main effects and supported interactions;
- the Generator displays catalog references beside Prompt selections, uses
  accessible single-track Steps/CFG range controls, and applies guidance only
  after an explicit user action;
- output geometry and LoRAs remain manual and outside all four optimizer modes;
- Analytics Overview reports coverage only, Prompt Combinations remains
  prompt-only, and Render Analytics exposes the same four modes and confidence
  vocabulary as the Generator;
- Analytics handoffs use the shared typed direct-navigation owner and are
  applied visibly in the Generator without staging UI or implicit drafts;
- one shared evidence carousel and the full-size image viewer are connected to
  Prompt references, Draft evidence and Analytics cards;
- the legacy `/api/v2/analytics/parameters` endpoint and the render branch of
  `/api/v2/analytics/combinations` are no longer active public structures.

### Canonical prompt content levels and shared media cards (completed feature slice)

- `PromptContentLevelPolicy` separates a typed catalog content level from free
  descriptive tags; canonical `content_level_*` markers override import-only
  legacy aliases;
- catalog and Playground V2 contracts expose `content_level`, and the catalog
  editor requires an explicit five-level choice;
- image visibility reads the stored generation snapshot or manual override only,
  eliminating catalog-edit drift across ranking, review, Arena, Analytics and
  Generator evidence;
- a complete revisions-bound 791-component curation was audited and recovered
  into a new validated v11 database; 44 components and 53 generations changed,
  and the prior runtime database remains backed up;
- true card collections share three equal tablet columns and natural uncropped
  media; Overview, Scopes and Render Analytics reuse the cyclic card-rail
  owner, while nested Playground carousels isolate touch/pointer gestures.
- normalized historical LoRA usage is graph-effective: disconnected or
  zero-strength branches remain raw provenance but cannot raise a generation's
  content level; the explicit v2 content audit found 208 such selections;
- Top/Worst includes every live image with at least one rating instead of
  reusing the three-image Analytics/Arena evidence threshold, and Settings
  exposes a real `Nicht eingestuft` LoRA state.

### Revisioned LoRA catalog and image handoff (implemented feature slice)

- schema v12 extends stable LoRA definitions with mutable display metadata,
  immutable default/trigger revisions and normalized trigger atom usages;
- legacy definitions receive an empty revision 1, while historical generation
  usages retain a `NULL` revision instead of borrowing current triggers;
- the Generator owns a separately ordered LoRA prompt layer and renders the
  selected revision's triggers as editable draft-only groups;
- `CompiledLoraGraphPolicy` proves exact ordered Model and dual-CLIP wiring in
  Blueprint v4 before persistence or provider submission;
- `ImageGeneratorHandoffService` returns independent authoritative Prompt and
  Render packages for visible image UIDs, including snapshot-only legacy and
  non-applicable multi-stage diagnostics;
- all card, carousel, viewer and inspector image surfaces reuse one
  `ImageGeneratorActions` owner and direct typed navigation;
- Settings remains a status surface; Catalog is the only LoRA editor.

### Generator handoff and lifecycle acceptance (implemented feature slice)

- `GeneratorHandoffNavigator` is the single outgoing owner; the target-side
  `GeneratorHandoffApplier` loads, projects, applies, persists, rolls back and
  cleans URL parameters atomically;
- `DraftSession` owns cancellation, revision rejection and the
  idle/preparing/ready/submitting state machine; editor changes immediately
  clear stale draft output;
- `GeneratorStatePersistence` serializes latest-write-wins saves and flushes
  the newest snapshot on navigation;
- schema v13 stores normalized Generator state in canonical SQLite and the
  explicit v12-to-v13 copy migration can import one validated legacy JSON
  snapshot without changing its source database;
- the Generator POST/preview routes, file repository, helper services,
  tab-local tray and duplicate toast/event paths were removed;
- Playwright proves exact LoRA weights through reload, draft, generation row,
  compiled loader and Fake-ComfyUI submission, with one trigger atom.

### Complete prompt attribution and trigger-based LoRA safety (implemented)

- schema v14 places content level on the immutable LoRA trigger revision; the
  definition-level field is dormant migration compatibility;
- `LoraUsagePolicy` requires both graph effect and an exact trigger in the
  matching positive/negative final-prompt scope; weights may differ;
- preview and submission reject a selected LoRA with all revision triggers
  removed before any generation persistence or ComfyUI call;
- hash-bound `legacy-provenance audit/recover` creates recognizable historical
  component and LoRA revisions, removes unsupported normalized LoRA rows,
  recomputes inferred levels and requires zero unattributed atoms or ambiguous
  bindings;
- complete image handoff replaces all seven component controls and the ordered
  LoRA layer with normal editable catalog state; unchanged input uses the
  authoritative snapshot and an explicit edit switches to `image_adapted`;
- Top-2/Top-3 are observed factors per character, where the character is the
  group and Scene, Outfit, Pose, Expression, Lighting, Modifier and evidenced
  LoRAs are the ranked factors.
- the explicit live promotion on 2026-10-07 preserved the v12 source, upgraded
  through v13 and v14, audited 414 generations with no unattributed atoms or
  ambiguous LoRA bindings, retained 19 evidenced LoRA usages and verified
  complete editable handoffs for all 393 active images;
- the closing shared gate passed 638 Python tests, 159 frontend tests and 12
  Playwright scenarios with 100% Python-Core and frontend statement coverage.

### Urgent corrective slice: atom identity and weight evidence (planned)

Status: required as soon as possible; documented on 2026-10-07, not yet
implemented or validated.

The structured-prompt slice made atom text and numeric weight separate columns,
but it incorrectly made both values part of immutable component-revision
truth. That conflates a stable atom with an experimental Playground usage and
fragments component history when only a weight changes. The existing
`atom_learning_stats` projection also lacks Character/component, component
revision and composition context, while edited prompt groups are flattened
before generation persistence and lose authoritative per-atom source
attribution.

The corrective slice must establish these invariants:

- normalized semantic content identifies an atom; changed content creates a
  different atom;
- component revisions change for structural atom membership, role or order,
  not for a per-generation weight experiment;
- every new generation persists actual atom weight plus explicit source layer,
  component and revision context where applicable;
- review/delete events produce rebuildable contextual atom-weight evidence and
  never mutate catalog facts;
- calculated recommendations expose support and uncertainty and do not claim
  causal proof from whole-image ratings;
- observed contexts are queried or projected from real generations without a
  precomputed Cartesian product;
- legacy source attribution is preserved only when provable and otherwise
  remains explicitly unknown;
- the schema migration writes and validates a new database, preserves images,
  generations, rendered prompt snapshots, reviews and stable identities, and
  never overwrites the source database in place.

Before implementation, the slice requires an explicit domain contract and
migration design covering catalog-authored defaults or constraints, duplicate
atoms across selected components, LoRA trigger sources, draft additions and
removals, historical overridden prompts and the context dimensions allowed in
the estimator. Completion requires behavior, rollback, migration, architecture
and analytics tests plus the complete shared quality gate.

## Final acceptance remaining

The previously completed implementation slices and their automated integration
gates remain valid for their stated scope, but the project is not at final
architectural acceptance while the urgent atom identity/weight correction
above remains planned. The live database upgrade/rebuild and real Blueprint-v4
Portrait/Landscape ComfyUI
smokes were completed successfully on 2026-10-05. On 2026-10-06 the owned
lifecycle worker completed the newest retained ComfyUI job, and the four jobs
whose history had expired were recovered through the explicit strict output
reconcile path. The live Review candidate was an unrated recovered output and
repeated Arena reads returned one stable pair without creating a match.
The content-level curation was also recovered and promoted from a new validated
schema-v11 output database on 2026-10-06; `main.py` was restarted on the LAN
after retaining the pre-recovery database backup.
The acceptance audit additionally repaired 165 historical generation snapshots
for the already-classified Explicit `example-lora-2.safetensors` LoRA
through the existing revision-checked preview/apply service. No name-based LoRA
heuristic or unreviewed bulk reclassification was introduced.
The generator dead-path audit and its automated acceptance are complete. In
addition to user-facing visual acceptance and opening the replacement pull
request, final integration now requires the corrective atom-identity and
weight-evidence slice above. No automatic merge is planned.

Each intermediate commit runs focused tests and static checks for changed
files. The targeted command is feedback only. Every completed slice and the
final integration require a successful full `python scripts/quality.py` run.

## Invariants for final acceptance

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
