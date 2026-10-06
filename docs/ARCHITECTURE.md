# ComfyReview Architecture

Status: canonical Review, Ranking, Arena, Curation, structured Prompt Catalog,
analytics, native Generation, schema-v12 application support and Frontend V2
including Settings are implemented on the active feature branch, 2026-10-06.
Final user acceptance and integration review remain open.

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

The canonical database has an explicit schema version. Schema v12 is the active
shape: it retains the v4 identity/review cutover, adds the v5 revisioned prompt
catalog, records v6 native output roles/content hashes, normalizes ordered
prompt-revision atom usages in v7 and adds workspace preferences, generation
profiles and normalized LoRA relations in v8. Schema v9 adds ordered workspace
content levels and explicit generation canvas dimensions. Schema v10 adds
output tiers and target geometry, stable LoRA catalog identities and immutable
generation snapshots, inferred generation content levels, plus append-only
manual image-classification events and their rebuildable projection. Stable `image_uid`
and `generation_uid` values are identity; PNG and optional sidecar paths are
mutable attributes.

Schema v11 adds only `image_geometry_projection`. It records actual PNG
dimensions, classified format/orientation, nearest 720/1080/2160 short-edge
class, the matched target dimensions, exact/approximate state and classifier
version. It is derived, rebuildable and never replaces image UID identity.

Schema v12 extends the existing stable LoRA identity into one canonical
catalog. `lora_revisions` is immutable and owns default Model/CLIP strengths
plus normalized positive/negative trigger atom usages. New
`generation_loras` rows reference the exact selected revision; legacy rows
stay `NULL` when no historic revision can be proven. Mutable display metadata
does not create a revision.

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

Schema v8 introduced workspace preferences and generation profiles. The
profile tables and generation profile columns remain dormant migration
compatibility in v12, but no active container service, V2 endpoint, Settings
surface or Playground flow reads them. Generations still record the exact
LoRAs they actually used. A loader is normalized only when a non-zero model or
CLIP branch reaches a consumed sampler input. Historical `loras_json` and raw
workflow graphs retain disconnected loader nodes as provenance, not as a
second writable runtime contract.

Schema v9 stores the enabled content-level sequence and the width/height owned
by generation profiles and concrete generation requests. One focused SQLite
predicate applies the same authored catalog-tag policy to every image-bearing
read model. Services and browser surfaces do not duplicate OR/AND or content
visibility semantics, and no path, prompt substring or image inspection is
used to infer a missing level at runtime.

Schema v10 separates automatic and manual classification. Automatic generation
classification is the strictest level from authored prompt-component tags and
the content-level snapshots of all graph-effective selected LoRAs. A current image override,
when present, wins in either direction. One shared SQLite visibility predicate
uses the effective level for Ranking, Review, Arena, Scope, Analytics and
evidence queries. Historical LoRA snapshots change only through an explicit,
revision-checked reclassification command; manual overrides are never rewritten.

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

`ReviewCandidateService` reads the workspace preference named
`review_prioritize_unrated`. When enabled, its repository returns visible
unrated images by descending canonical image ID before falling back to rated
images with the oldest rating sequence. When disabled, the same repository
uses the oldest review sequence directly. The legacy SQLite column
`review_unrated_only` stores this renamed preference for compatibility; it is
not interpreted as an exclusion filter.

## 5. Ranking and Arena

`RankingService.list_images()` reads canonical images, review aggregates and
curation state. Top/Worst includes every live image with at least one rating;
larger evidence thresholds remain Analytics/Arena policy and cannot silently
remove low-count images from the gallery. Model, character, set and scope
filters still apply while deleted images remain excluded.

`ArenaService.next_pair()` delegates to `FairArenaPairingPolicy`. The repository
returns played directions plus the latest canonical match containing every
candidate. Never-used and longest-waiting images sort first; stable pool rank
and image UID resolve ties. A reverse direction remains eligible, but both
images move to the newest rotation position after a decision, preventing an
immediate rematch. Repeated reads without a decision return the same pair.
`record_decision()` accepts image UIDs; its repository stores the match and both
resulting rating events in one SQLite transaction.

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

`legacy-provenance audit/recover` is the bounded follow-up for retained
generation evidence that became available after that import. It is an offline
migration adapter, never a runtime fallback. Embedded recipe snapshots and
unique exact matches are accepted mechanically; semantic reconstruction is
accepted only from the versioned reviewed manifest. Evidence classes remain
visible in the audit report. Recovery creates and validates a different output
database, keeps recovered one-off components archived and inserts historical
revisions below the unchanged current revision.

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

FastAPI owns one `GenerationLifecycleWorker` in its application lifespan. It
starts only after successful schema validation, polls a bounded active set
every two seconds and stops through an owned stop signal. Its coordinator never
resubmits work: interrupted local `prepared` records fail locally, ambiguous
`submitting` records require reconciliation, and confirmed `submitted` or
`running` records are observed through `GenerationService`. Provider timeouts
and connection errors preserve the current status for a later pass; definitive
failure, completion and unknown prompt identity become canonical transitions.
No SQLite transaction remains open during provider or filesystem access.

Explicit reconciliation is the only filesystem-recovery path. If a retained
ComfyUI prompt is unknown, a bounded provider searches only the persisted
output subdirectory and exact filename prefix. It accepts one unambiguous PNG
for the expected output binding and then reuses the normal hash, output,
metadata and geometry collector. Missing, additional or path-escaping matches
remain `reconciliation_required`; automatic resubmission and fuzzy filename
matching do not exist.

Blueprint v4 maps `output_width` and `output_height` roles into a fixed
AnimeSharp path: `VAEDecode -> 4x-AnimeSharp -> ImageSharpen -> Lanczos
ImageScale -> SaveImage`. `GenerationGeometryPolicy` derives those target
dimensions from a 720p, 1080p or 2160p short edge without cropping. Required
nodes and `example-upscaler.pth` are discovered at the provider boundary and are
validated before persistence or submission.

## 9. Schema lifecycle

Runtime startup validates only the supported canonical schema; it never
upgrades an unsupported database silently. Canonical v3 through v12
changes are available only through `python -m comfyreview canonical-db
upgrade --output PATH` and are backed up. The v3-to-v4 step migrates writable legacy review
state into events, projects delete tombstones and replaces old tables with
read-only views; v5 adds the prompt catalog and v6 stores native output role
and content-hash provenance. Schema v7 adds normalized revision atom usages;
the v6-to-v7 upgrade parses only the supported grammar and validates the
structured roundtrip before commit.

The v9-to-v10 step is likewise explicit: it creates and validates a separate
output database first, retains the original as a backup, and only then replaces
the configured runtime database. Existing default-character profiles move to
Blueprint v4 and receive the 1080p output tier; historical image visibility is
preserved until an operator explicitly applies a LoRA reclassification.

The v10-to-v11 step uses the same backup/new-file/validate/install lifecycle
and creates an empty projection. `python -m comfyreview canonical-db
rebuild-image-geometry` then scans PNG headers outside SQLite write
transactions and replaces the projection atomically; missing or damaged files
are returned as diagnostics.

The v11-to-v12 step copies the source to a separate output database, creates
base revision 1 for every existing definition, preserves historical usage with
a nullable revision link, validates integrity and verifies that the source hash
did not change. Promotion of that output remains an explicit operator action.

`CompiledLoraGraphPolicy` runs after semantic v4 compilation and before any
generation row or ComfyUI submission. It requires one ordered loader per
selection, exact provider filenames/weights, an unbroken Model route to the
sampler and an unbroken CLIP route to both encoders. The provider still sees
only the finished graph. `ImageGeneratorHandoffService` independently exposes
authoritative prompt and render packages for visible image UIDs. Prompt
handoffs expose stable component IDs so every image-originated transfer fills
the visible Playground selection controls; historical prompt snapshots remain
provenance and are not used as a hidden generator input.

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
- Playground V2 loads and saves one complete generator-control snapshot through
  `/api/v2/playground/generator-state`. The injected settings service preserves
  the existing server-owned UI-state file, migrates legacy render values on
  first read and keeps explicit cross-surface handoffs as the final override.
- `CyclicCardRail` is the single browser lifecycle owner for cyclic collection
  navigation. Playground character rows and Analytics Overview/Scope/Render
  collections configure that component instead of duplicating wheel, touch or
  wrap-around listeners; each card retains its independent evidence carousel.
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

`WorkspacePreferencesService` owns active mutable canonical preferences.
Historical profile services remain offline compatibility code only and are not
composed into the runtime. `RuntimeDiagnosticsService`
combines an injected, read-only configuration snapshot with the shared
ComfyUI capability cache. The Settings HTTP and browser layers do not read or
write `.env`, open SQLite or call ComfyUI directly. Connection checks are
explicit provider calls; ordinary Settings reads return cached capability state
without blocking on the external service.

Content levels are cumulative user choices beginning with mandatory
`standard`. `PromptContentLevelPolicy` maps exactly one canonical
`content_level_*` metadata marker to the typed `ContentLevel` on every catalog
component. `nsfw_level_*` and the older authored aliases remain import
fallbacks only; a canonical marker always wins. Descriptive tags no longer
carry content-policy meaning. New generation snapshots derive their level from
typed component levels and LoRA snapshots, while all historical image readers
use only the stored generation level or a manual image override.
The Generator owns direct sampler and LoRA choices plus semantic format and
resolution-class values. `GenerationGeometryPolicy` maps those choices to the
fixed matrix before Blueprint v4 compilation.

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

`RenderGuidanceService` is the single active calculation boundary used by the
Generator and Render Analytics. Its repository reads stable image identity,
normalized generation/stage values and immutable review/delete events. The
service returns observed setups, observed parameter values, modeled parameter
effects, modeled discovery setups, current-selection assessment and coverage.
Independent image counts define support; repeated review events affect evidence
weight but never inflate the five-image stability threshold.

The `render-guidance-v1` policy uses beta-smoothed evidence, conservative
observed ordering, shrunk main effects and only sufficiently supported pair
interactions. Candidate enumeration is bounded to known provider values and is
streamed into a fixed result heap; it is not persisted and does not materialize
the full prompt/render Cartesian product. Provider capability discovery is
applied by `PlaygroundRenderGuidanceService`, outside the scoring policy.

`GET /api/v2/analytics/render` and
`POST /api/v2/playground/render-guidance` share these types and presenters.
The former exposes the observed/predicted × setup/parameter matrix; the latter
adds capability filtering for the current Generator. LoRAs, seed and output
geometry are deliberately absent from this optimizer contract. Prompt
combinations remain a separate canonical composition query. Image URLs are
added only at the HTTP presentation boundary from stable image IDs.

`AnalyticsService.observed_combinations_by_character` groups those observed
composition facts by stable character UID and applies the result limit inside
each group. The Playground presenter therefore receives independently ranked
Top-2 and Top-3 rows without deriving character identity in the browser.

## 11. Observability and quality

Request middleware validates or generates `X-Request-ID`, binds it through a
context variable, returns it on responses and emits structured JSON lifecycle
events without prompts, credentials or full local paths. Review, Arena,
Curation and migrations log state transitions and normalized failures.

Architecture tests enforce dependency direction, SQL placement and provider
ownership. New concrete core callables require manifest entries and behaviour
tests; the defined core scope retains 100% statement coverage. The complete
gate is `python scripts/quality.py`.
