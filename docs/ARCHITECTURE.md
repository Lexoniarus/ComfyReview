# ComfyReview Architecture

Status: canonical Review, Ranking, Arena, Curation, structured Prompt Catalog,
analytics, native Generation, schema-v16 application support and Frontend V2
including Settings are implemented and integrated on
`refactor/review-boundary`, 2026-10-07. Final user acceptance and eventual
integration into `master` remain open.

## 1. Product boundary

ComfyReview is a local-first application for discovering ComfyUI outputs,
reviewing and comparing images, assigning curated sets, analysing review data
and handing reproducible settings back to ComfyUI. Character Chronicles
campaign, Champion, VN, social, embeddings and RAG systems are outside this
refactor.

A functional Card Battler prototype is an approved post-refactor ComfyReview
product target, not current runtime behaviour or a refactor acceptance
requirement. Its manual card-development, deterministic-rules, deck,
server-authoritative PvE and battle-driven evolution boundaries are defined in
the [Card Battler target](CARD_BATTLER_TARGET.md). Character Chronicles may
later reuse that bounded implementation without becoming a runtime dependency
of ComfyReview.

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

### 2.1 Card Battler model resource

The pre-persistence Card Battler implementation reads design and rules facts
from the external `card_battler.sqlite3` model database. The composition root
creates one `SqliteCardBattlerModelResource` and injects it into focused SQLite
read adapters. On first access that owner performs the complete database
identity, schema-v3 table/column contract, integrity, foreign-key, active
ruleset and active-policy validation exactly once per application container.
The validated snapshot or its typed failure is cached for that resource
lifetime. Adapters subsequently use only short-lived `mode=ro`, `query_only`
connections; the model resource never creates schema, repairs data or opens a
writable connection. Replacing the file requires a new application container
or process restart.

Schema requirements are registered in named read-area groups. A model table
cannot become authoritative for a new adapter until its required columns are
part of the shared validation contract. This database remains model/design
input only; no card identity or other runtime game fact is persisted before
the post-proof persistence phase.

## 3. Canonical identity and runtime data

The canonical database has an explicit schema version. Schema v16 is the active
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

Schema v13 adds the normalized Playground Generator state. One render/seed
singleton owns scalar controls, prompt-selection rows own each role and mode,
and ordered LoRA rows reference exact stable definitions and immutable
revisions with Model/CLIP strengths in milli-units. The old UI JSON is an
optional explicit migration source, never a runtime repository.

Schema v14 makes the immutable LoRA trigger revision the owner of its typed
content level. A normalized generation LoRA must reference that exact revision,
be graph-effective on Model or CLIP and have at least one exact trigger in the
matching final prompt scope. The former definition-level content field is
dormant migration compatibility, not an application or HTTP truth.

Schema v15 adds prompt candidates, exact generation prompt groups and
append-only promotion facts. Schema v16 adds append-only manual-variant
selection facts without changing candidate recipe identity. Sections 10.2 and
10.3 describe the active guidance and analytics boundaries.

Canonical v4 facts include:

- images and generation provenance;
- append-only `review_events`;
- `arena_matches` linked to images;
- one `curation_assignments` relation per image.

Canonical v5 additionally includes stable prompt components, immutable prompt
revisions, explicit compositions and source mappings for audited legacy
imports. Catalog metadata can change without rewriting revision content.
Schema v7 makes ordered positive/negative atom usages with separate numeric
weights part of authored revision truth. This is correct for an immutable
catalog revision because it represents one exact stable standard recipe. Weight
does not become part of atom identity: Playground experiments with another
weight remain draft or generation observations until an exact observed recipe
is promoted as a new component revision. Evidence-based promotion now selects
the current stable revision, while the Generator keeps latest-manual,
calculated and next-test variants separate. Rendered whole-prompt columns
remain derived immutable snapshots, not writable API inputs.

Schema v8 introduced workspace preferences and generation profiles. The
profile tables and generation profile columns remain dormant migration
compatibility in v16, but no active container service, V2 endpoint, Settings
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

Schema v10 separates automatic and manual classification. In the current v16
runtime, automatic generation classification is the strictest level from
authored prompt-component tags and the content-level snapshots of
graph-effective, trigger-evidenced LoRA revisions. A current image override,
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
Component-scoped overrides bind kind, component UID, revision UID and optional
candidate UID to an exact fixed selection. They alter only the transient
rendered group and are rejected when the binding is missing, duplicated or no
longer selected. `PlaygroundVariantPreparationService` prepares up to twelve
transient drafts with selection entropy independent from the concrete image
seed. `PlaygroundVariantDiversityPolicy` prefers unique resolved prompt and
sampler signatures, reports exhausted diversity explicitly and never persists
the prepared batch.
Each selection pairs the unchanged current `PromptComponent` metadata with an
explicit `SelectedPromptComponent.revision`; a historical fixed selection
therefore remains exact without redefining `latest_revision`. Compatibility
checks and draft response groups use the selected revision's immutable content,
while random and revision-unspecified fixed selections use the current latest
revision.
Draft responses publish ordered `prompt_selections` containing kind, stable
component UID and exact immutable revision UID. Generation submission returns
that typed selection to `PlaygroundService.confirm_draft`; it never reduces a
reviewed draft to component IDs or resolves it through `latest_revision` again.
An archived component remains excluded from new/random selection but its exact
historical revision remains reproducible when explicitly bound by a draft.
Submission uses the native `GenerationService`; there is no interim generation
facade or dual-write.

Reviewed variant batches cross a separate typed submission boundary. The V2
adapter accepts at most twelve concrete sampler setups and rejects legacy sweep
controls there. `PlaygroundSubmissionService.submit_variants` invokes the
existing generation boundary once per draft, preserves request order and
associates every success or failure with the originating draft UID. Partial
provider failures therefore remain an inspectable batch result; no database
transaction spans multiple provider submissions.

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
upgrades an unsupported database silently. Canonical v3 through v14
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

The v12-to-v13 step creates the normalized Generator tables in that new output
database. `--generator-state PATH` may import one strictly validated
`generator_v2` snapshot; missing stable Prompt/LoRA revisions or any invalid
field abort the output migration. The v12 source remains byte-identical and
runtime startup refuses it until an operator promotes the validated v13 copy.

The v13-to-v14 step adds the revision-owned LoRA content level and backfills
each immutable revision from its legacy definition value. The separate
hash-bound `legacy-provenance audit/recover` workflow then proves exact trigger
usage, removes only unsupported normalized LoRA rows, recomputes affected
generation levels and requires zero unattributed atoms and zero ambiguous LoRA
bindings before its copied output can be promoted.

`CompiledLoraGraphPolicy` runs after semantic v4 compilation and before any
generation row or ComfyUI submission. It requires one ordered loader per
selection, exact provider filenames/weights, an unbroken Model route to the
sampler and an unbroken CLIP route to both encoders. The provider still sees
only the finished graph. `ImageGeneratorHandoffService` independently exposes
prompt and render packages for visible image UIDs. Prompt handoffs project the
ordered canonical scopes as typed selections containing kind, stable component
ID, exact immutable revision ID and composition position; duplicate kinds are
reported as inconsistent canonical data rather than normalized. Existing
parallel component/revision ID lists remain compatibility fields. Revision IDs
resolve the immutable prompt atom usages; historical generation prompt
snapshots remain separate provenance and are not used as a substitute.
For a complete image handoff, those exact historical revisions populate the
normal editable Generator slots and ordered LoRA controls. Unchanged handoffs
render from the authoritative image snapshot; after an explicit slot edit,
`image_adapted` replaces only that group on the server. Incomplete attribution
remains viewable as a snapshot but cannot claim editable provenance.

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
  `/api/v2/playground/generator-state`. The injected application service uses
  only the normalized SQLite repository; the route owns JSON translation and
  contains no persistence rule.
  `PromptModeEditor` owns each prompt kind's mode, component UID and optional
  immutable revision UID. Fixed selections persist and submit that exact UID;
  old states without one and deliberate component changes use the catalog's
  current latest revision. The Generator catalog includes active components
  plus archived historical components required by exact image handoffs; the
  latter are visibly marked and remain excluded from all random candidates.
  The browser treats restored revision UIDs as opaque bindings;
  authoritative existence, component ownership and content validation remain
  in the Application layer. Random/off choices carry no revision binding.
  Fixed Setup groups expose experiment-local component overrides only when the
  exact component, revision and optional candidate identity matches. The
  browser sends those typed bindings to the existing Playground application
  boundary; it never mutates catalog state implicitly. An explicit candidate
  action remains the only catalog materialization path.
  `PlaygroundVariantPreparationService` composes the existing selection and
  draft service with injected selection entropy, sampler variation and a pure
  diversity signature. Selection entropy is independent from the requested
  image seed, so a fixed render seed does not collapse random catalog choices.
  Prepared batches are transient and carry diversity metadata rather than a
  persisted draft record. `VariantSession` is the browser owner for request
  cancellation, active/selected draft UIDs, reviewed payloads and stale state.
  `VariantBoard` and `VariantInspector` render that state; the controller only
  orchestrates API and view transitions. `PlaygroundWorkspace` owns both the
  primary Setup/Varianten navigation and the responsive presentation state:
  paired desktop panes, a laptop Inspector drawer and tablet board/Inspector
  tabs. It also owns and disposes every listener for those transitions.
  The reviewed batch submission boundary accepts no more than twelve concrete
  one-job payloads. It invokes the existing submission service per variant,
  outside an open SQLite transaction, and returns ordered successes and
  failures keyed by `draft_uid`. Legacy single-draft and sweep endpoints remain
  compatibility contracts and are not used by the experiment workspace.
  Browser prompt handoffs
  have no direct draft-reference path: every supported Image, Scope,
  Composition and Top Combination action navigates directly to the Generator
  and applies to the ordinary visible state before explicit draft creation.
  The controller reloads typed prompt selections and canonical ordered LoRAs
  from an image handoff, applies them atomically as a complete editor-state
  replacement and persists the ordinary snapshot before removing the handoff
  URL parameters. Rejected or unpersisted applications restore the prior state
  and retain those parameters. Applying a handoff does not create a draft.
  Canonical image summaries expose normalized, revision-bound LoRA usages so
  shared cards and inspectors show the same LoRA factors that the handoff
  applies; raw or triggerless loader provenance is not presented as usage.
  Analytics Scope actions carry only a typed component/revision source and
  patch that prompt kind; Analytics Composition actions carry only the
  composition UID, resolve its exact ordered revisions through one
  Application `PromptSelection` operation, and replace the complete prompt
  selection. The Composition draft renderer and API handoff project this same
  validated selection, including active-component, content-level, historical
  revision, Character and unique-kind rules. Multiple typed prompt sources in
  one intent are rejected visibly at the beginning of controller startup,
  before editor rendering, saved-state restore, handoff, persistence or
  cleanup. Both single-source Scope and Composition actions apply through the
  shared rollback/persist operation and clear only their typed source after the
  normal generator state is saved. Top Combinations carries a typed combination
  source containing exact kind/component/revision selections plus applicable
  LoRA revisions and strengths. The `two_additional_factors` and
  `three_additional_factors` response fields count observed factors beside the
  always-present Character. Their producer rejects incomplete or unavailable
  factors before the stateless projector applies the exact selection. After
  successful apply and generator-state persistence, only that typed source is
  removed from the current URL. The injected URL cleanup preserves unrelated
  query parameters; failed or ambiguous handoffs leave the source URL
  untouched. There is no tab-local intent store, global staging event, tray or
  duplicate toast owner. Legacy
  component/revision/composition/image browser intent fields and Store-v1
  prompt handoffs are no longer consumed; direct draft-source compatibility
  remains isolated at the HTTP API boundary.
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

#### Prompt-variant guidance and evidence-based promotion

The boundary reuses one `prompt_atoms` identity when only a weight changes.
Catalog revisions include weights because each revision is the exact standard
recipe that was valid at that point in catalog history. The active standard is
selected by the newest append-only promotion rather than revision number.

`PromptVariantGuidanceService` parallels render guidance while keeping three
independent results for every loaded prompt component:

1. the stable observed variant is the revision selected by the newest promotion
   event. Revision 1 starts as a provisional standard and remains selectable
   before enough evidence exists;
2. the latest manual catalog variant is the most recently authored prompt or
   weight change, independent of whether it has been generated or promoted;
3. the calculated optimized variant is a derived, weight-only estimate for the
   promotion-selected stable atom list and may not yet have been observed as
   one exact recipe;
4. the next useful test is a bounded discovery candidate selected by uncertainty
   as well as expected result and differs from both the current and optimized
   recipes.

Every choice loads only into that component's ordinary editable atom group in
the Generator. Generating and rating a candidate turns it into an observed exact
recipe. After successful Review, Delete or Arena persistence, an injected
coordinator automatically reconciles affected components in a separate short
transaction. It may reuse an identical immutable revision or append one and
then appends a promotion event with the previous standard, evidence frontier,
policy version and reason. Older revisions and their historical generation
bindings remain unchanged. A failed reconciliation never rolls back the review;
it is reported as pending and can be repeated idempotently by an explicit audit
command.

`prompt-guidance-v1` uses the Render Guidance evidence semantics. Stability
requires five independent images for an exact recipe; repeated reviews change
evidence weight but not image support, and deletes remain negative evidence.
Observed recipes are ordered conservatively by lower-bound score before
expectation, average and support. A supported challenger replaces the current
standard only with at least `0.02` lower-bound advantage, except when the
current standard is provisional or no longer sufficiently supported. Evidence
is component-global rather than checkpoint-, character- or scene-specific.

Calculated guidance never changes text, membership, role or order. For each
stable atom it considers supported observed weights and `0.05` intermediate
values inside the supported minimum/maximum range, never extrapolation. An
observed weight anchor requires three independent images and interpolation
requires two supported anchors; otherwise the current weight is retained.
Effects are shrunk against the component baseline and combined as the mean of
modeled logit effects so longer atom lists gain no structural advantage. The
next test maximizes `mean + 1.645 * standard_deviation`, may change several
weights, and is selected without materializing a Cartesian product.

Schema v15 stores normalized component candidates, exact per-generation prompt
groups and atom usages, and append-only promotion facts. Draft and generation
contracts carry concrete source revisions and optional candidate identities per
group; the application service validates ownership and exact prompt rendering
before the repository commits all generation facts atomically. A manual content
edit creates a candidate rather than immediately changing the standard.
Historical flattened usages are attributed to components only when their
partition is provable; ambiguous records remain unknown and are excluded from
component guidance. Derived summaries remain rebuildable and whole-image
ratings remain contextual evidence, not causal proof for one atom.

Schema v16 adds append-only manual-variant selection facts. Candidate recipes
remain content-deduplicated, while the separate selection history preserves
the latest manual A→B→A choice even when that recipe was first calculated,
has already been generated or is now also the promoted stable revision.

`POST /api/v2/playground/prompt-guidance` accepts the component and expected
stable revision; the read service loads the stable atoms and rejects stale
revision bindings. `POST /api/v2/playground/prompt-candidates` materializes a
calculated or manually accepted result only on explicit selection. The browser
stores the concrete candidate identity alongside the source revision and loads
only that component's atoms into the normal editor. Review, Delete and Arena
services invoke an injected `PromptPromotionCoordinator` after their canonical
write has committed. Reconciliation uses its own short transaction; failures
are logged and surfaced as `promotion_pending`. The offline
`prompt-promotions audit|reconcile` command uses the same idempotent coordinator.

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

`AnalyticsService.observed_combinations_by_character` groups the complete
ranked candidate set by stable character UID for an explicit additional-factor
count. `PlaygroundCombinationSelectionPolicy` then fills the two- and
three-additional-factor groups in alternating passes, preferring a distinct
best-image UID across both groups before deterministically falling back to the
remaining ranked candidates. The Playground presenter only translates that
selection and never derives character identity or diversity in the browser.

## 11. Observability and quality

Request middleware validates or generates `X-Request-ID`, binds it through a
context variable, returns it on responses and emits structured JSON lifecycle
events without prompts, credentials or full local paths. Review, Arena,
Curation and migrations log state transitions and normalized failures.

Architecture tests enforce dependency direction, SQL placement and provider
ownership. New concrete core callables require manifest entries and behaviour
tests; the defined core scope retains 100% statement coverage. The complete
gate is `python scripts/quality.py`.
