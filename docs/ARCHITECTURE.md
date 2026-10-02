# ComfyReview Architecture

Status: canonical Review, Ranking, Arena, Curation, structured Prompt Catalog,
analytics, native Generation, live schema-v8 data and Frontend V2 including
Settings are implemented on the active refactor branch, 2026-10-02. Final user
acceptance and integration review remain open.

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
`ApplicationContainer` owns runtime-only typed settings, the canonical schema
lifecycle, output catalog and application services. The FastAPI lifespan
prepares runtime directories and validates or initializes only the supported
canonical schema. Root `app.py` and `main.py` remain compatible entry points.
Legacy database paths live in a separate `LegacyMigrationSettings` object used
only by explicit audit, import and maintenance commands.

## 3. Canonical identity and runtime data

The canonical database has an explicit schema version. Schema v8 is the active
shape: it retains the v4 identity/review cutover, adds the v5 revisioned prompt
catalog, records v6 native output roles/content hashes, normalizes ordered
prompt-revision atom usages in v7 and adds workspace preferences, generation
profiles and normalized LoRA relations in v8. Stable `image_uid`
and `generation_uid` values are identity; PNG and optional sidecar paths are
mutable attributes.

Canonical v4 facts include:

- images and generation provenance;
- append-only `review_events`;
- `arena_matches` linked to images;
- one `curation_assignments` relation per image.

Canonical v5 additionally includes stable prompt components, immutable prompt
revisions, explicit compositions and source mappings for audited legacy
imports. Catalog metadata can change without rewriting revision content.
Schema v7 makes ordered positive/negative atom usages with separate numeric
weights the authored revision truth. Rendered whole-prompt columns remain
derived immutable snapshots, not writable API inputs.

Schema v8 makes workspace preferences and generation profiles canonical.
Profiles own sampler defaults, range policies, seed policy, batch size and an
ordered LoRA stack with separate Model and CLIP strengths. Generations record
the exact LoRAs they actually used. Historical `loras_json` remains provenance,
not a second writable runtime contract.

`images.deleted_at`, `current_image_reviews`, `image_review_summary` and ranking
results are projections derived from canonical facts. The old `image_reviews`
and `deleted_images` names exist only as read-only compatibility views. No
repository writes a second current-review truth.

The following legacy databases remain available only as explicit historical
audit/import sources or for the `legacy-db` maintenance command:

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

Playground preview preparation reads this catalog through `PlaygroundService`,
applies `PromptSelectionPolicy` and renders concrete revision snapshots through
`PromptRenderer`. Draft prompt overrides do not mutate catalog revisions.
Submission uses the native `GenerationService`; there is no interim generation
facade or dual-write.

Historical generation relationships are completed only through the explicit
`legacy-compositions audit/import` tool. The audit reads both databases in
SQLite read-only mode, binds them by SHA-256 and recognizes complete canonical
prompt-atom sequences in variable ordered slot sets. The importer links only
uniquely determined revision memberships and never overwrites prompt snapshots,
generation lifecycle or output provenance. Extra historical text remains a
draft override in the immutable snapshot; ambiguous and insufficient evidence
stays unlinked and is available only as a migration diagnostic.

## 8.1 Generation boundaries

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

Runtime startup validates only the supported canonical schema; it never
upgrades an unsupported database silently. Canonical v3 through v7
changes are available only through `python -m comfyreview canonical-db
upgrade` and are backed up. The v3-to-v4 step migrates writable legacy review
state into events, projects delete tombstones and replaces old tables with
read-only views; v5 adds the prompt catalog and v6 stores native output role
and content-hash provenance. Schema v7 adds normalized revision atom usages;
the v6-to-v7 upgrade parses only the supported grammar and validates the
structured roundtrip before commit.

The older multi-file schema lifecycle remains centralized in
`comfyreview.repositories.sqlite.legacy_schema`. Its explicit
`legacy-db upgrade` command handles only known additive changes. This does not
claim crash atomicity across several SQLite files.

## 10. Final integration boundaries

The canonical cutover is intentionally not the end of the wider refactor.

- Remaining older `services/*` modules require the final usage and
  responsibility audit; active HTTP/view preparation stays, obsolete
  compatibility facades do not.
- Frontend V2 uses native ES modules, one shared API client, lifecycle-owned
  requests and focused view/controller classes. Playwright verifies bounded
  rendering and all required desktop/tablet viewports.
- Live canonical data completion is validated. ImageContext and scope queries
  can now use exact composition memberships for 363 generations; the sixteen
  unresolved cases remain explicit diagnostics rather than guessed relations.
  Application ImageContext will remain free of HTTP URLs; a response mapper
  combines it with `OutputFileUrlMapper` at the presentation boundary.

Existing projection workers are not migration targets by default. Each derived
dataset is first evaluated for replacement by a direct query or canonical SQL
view. A new idempotent worker is introduced only for a projection whose
materialization is demonstrably necessary.

The completed audit is recorded in `docs/PROJECTION_AUDIT.md`. It found no
current projection requiring replacement materialization: canonical repository
queries are the chosen cutover for rankings, prompt statistics, observed
composition statistics, recommendations and best-image lookup. The legacy
worker/jobs/cursors and their runtime have been removed.

Legacy sources may be read by explicit migration tools. They must not become a
second writable truth for an already cut-over feature.

### 10.1 Settings and runtime diagnostics

`WorkspacePreferencesService` and `GenerationProfileService` own mutable
canonical settings through focused repository ports. `RuntimeDiagnosticsService`
combines an injected, read-only configuration snapshot with the shared
ComfyUI capability cache. The Settings HTTP and browser layers do not read or
write `.env`, open SQLite or call ComfyUI directly. Connection checks are
explicit provider calls; ordinary Settings reads return cached capability state
without blocking on the external service.

### 10.2 Structured prompt boundary

`PromptAtomUsage` carries normalized text and `weight_milli`. Catalog write
commands, Playground draft overrides and V2 generation submission accept
ordered positive/negative usages rather than an arbitrary final prompt string.
`PromptRenderer` alone produces the rendered snapshots supplied to
`GenerationService` and ultimately `WorkflowCompiler`. Repositories persist
the normalized usage relation but do not format prompts. The ComfyUI provider
remains unaware of atoms, weights and catalog roles.

The Catalog and Playground editors use a lifecycle-owned `PromptAtomEditor`.
Edits affect a draft copy, can be reordered/reset, and never mutate the source
revision. The legacy HTML form adapter may parse the supported combined-string
grammar at its explicit compatibility boundary; it does not reintroduce a
whole-string application contract.

### 10.3 Canonical analytics boundaries

Render analytics no longer treat a serialized `combo_key` as a technical
configuration. `RenderAnalyticsService` separates marginal recommendations
from actually observed complete render setups. The SQLite repository builds
the latter from canonical generation columns plus ordered
`generation_sampler_stages`; seed is intentionally excluded from grouping.
`CompositionAnalyticsService` independently exposes canonical prompt
compositions and the render setups observed for one composition.

The HTTP boundary exposes summary, one selected parameter dimension, prompt
combinations and render setups as distinct queries. Parameter tabs therefore
load only their requested dimension, while prompt-combination details obtain
their technical setups through a focused endpoint. The browser neither parses
`combo_key` nor calculates statistics. Image URLs remain response-mapping
concerns. Application-owned static assets require cache revalidation so a new
ES-module entry point cannot leave its dependency graph silently stale.

## 11. Observability and quality

Request middleware validates or generates `X-Request-ID`, binds it through a
context variable, returns it on responses and emits structured JSON lifecycle
events without prompts, credentials or full local paths. Review, Arena,
Curation and migrations log state transitions and normalized failures.

Architecture tests enforce dependency direction, SQL placement and provider
ownership. New concrete core callables require manifest entries and behaviour
tests; the defined core scope retains 100% statement coverage. The complete
gate is `python scripts/quality.py`.
