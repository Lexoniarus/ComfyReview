# ComfyReview Data Architecture

**Dokumentklasse:** `CURRENT_TECH_REFERENCE` – heutiger Canonical-v18-Codevertrag; privater DB-Cutover und historische Operatorzahlen getrennt.

Status: source-verified canonical SQLite schema **v18** at ComfyReview
`refactor/review-boundary`, pre-import code commit `a5f4131` (2026-10-09).
See [schema implementation](../comfyreview/repositories/sqlite/canonical_schema.py)
and [code/CI audit](IMPLEMENTATION_AUDIT.md). Runtime migration commands
exist, but user-specific DB upgrades, cutovers, historical counts and private
reports cannot be independently verified from this repository.
Generation-profile tables are retained as **dormant migration compatibility**.

> **In-progress boundary:** Schema v18 is the **implemented code contract**,
> not proof that a private runtime database has already undergone the
> normalized catalog cutover. Operator review/acceptance and database
> optimization are still underway. The current design is a maintainable
> ComfyReview snapshot, **not** a fixed future Character Chronicles schema.
> [Active Work](ACTIVE_WORK.md).

## 1. Source-of-truth rule

Every business fact has one writable authoritative home. Review, Arena and
Curation runtime writes now go only to `comfyreview.sqlite3`; the old files are
read-only import sources for these concerns. There are no dual-writes.

Stable IDs are identity. Paths are mutable evidence and file attributes:

```text
image_uid = "..."
png_path = "E:/ComfyUI/output/.../image.png"
```

Changing a path does not change the image UID or any review, match or curation
relationship.

## 2. Canonical schema v18

The canonical database uses explicit schema metadata and foreign keys. Schema
v18 contains the v4 identity/review cutover, the v5 prompt catalog, v6 native
output provenance, v7 normalized prompt-revision atom usages, v8 workspace
settings/generation profiles, v9 content/canvas settings and v10 output/content
classification facts together with the v11-to-v18 additions listed below:

- `generations` and normalized generation provenance;
- `images` with stable UID, output role, content hash, current paths and
  `deleted_at`;
- append-only `review_events`;
- `arena_matches` referencing images;
- `curation_assignments` with one assignment per image;
- `prompt_components` with stable component UIDs and mutable metadata;
- immutable `prompt_revisions`;
- ordered `prompt_revision_atom_usages` with positive/negative scope,
  position and `weight_milli` linked to canonical `prompt_atoms`;
- `prompt_compositions` and their concrete revision membership;
- singleton `workspace_preferences` and ordered
  `workspace_curation_set_order`;
- ordered, non-empty `workspace_content_levels` (default `standard`, but
  selectable without it; visibility matches the effective image level);
- stable-UID `generation_profiles` and ordered
  `generation_profile_loras`;
- explicit width/height on generation profiles and concrete generations;
- profile output tier plus concrete generation target width/height;
- canonical `lora_definitions` with stable UID, current provider filename,
  display metadata, dormant legacy content field and archive state;
- immutable `lora_revisions` plus ordered normalized trigger-atom usages and
  default Model/CLIP strengths, with the typed content level owned by the
  revision;
- normalized `generation_loras` recording stable LoRA identity, filename and
  content-level snapshot actually used, with an exact revision link for new
  generations; after v14 provenance recovery every retained normalized usage
  has an exact revision and scoped trigger proof;
- inferred generation content level;
- append-only `image_content_level_events` and rebuildable
  `image_content_level_state` for manual overrides;
- rebuildable `image_geometry_projection` keyed by image ID with actual
  dimensions, format, resolution class, target match and classifier version;
- singleton `playground_generator_state`, prompt-role selection rows and
  ordered revision-pinned `playground_generator_loras`;
- deduplicated `prompt_component_candidates` with ordered atom usages;
- exact prompt groups and atom usages for each attributed generation;
- append-only `prompt_component_promotions`, whose newest event selects the
  current standard revision;
- append-only `prompt_component_manual_variants`, which preserves the latest
  authored catalog-test selection independently of promotion;
- versioned current image catalog compositions, independent of immutable
  generation compositions and complete prompt snapshots;
- versioned global quality/content policies and exact generation policy links;
- canonical atom/render evidence baseline runs plus rebuildable learning
  projections;
- `prompt_components.catalog_role`, separating selectable catalog entries from
  generation-only provenance;
- rebuildable current-state and aggregate views.

Unknown or unsupported versions fail at startup. Runtime startup never performs
a v3-to-v4, v4-to-v5, v5-to-v6, v6-to-v7, v7-to-v8, v8-to-v9, v9-to-v10,
v10-to-v11, v11-to-v12, v12-to-v13, v13-to-v14, v14-to-v15, v15-to-v16,
v16-to-v17 or v17-to-v18
migration. The explicit, backed-up command is:

```text
python -m comfyreview canonical-db upgrade --output PATH [--backup-dir PATH] \
  [--generator-state PATH]
```

## 3. Review history and current state

Schema v4 intentionally changes reviews from a writable current-state table to
an append-only canonical history. Each `review_events` row has a stable event
UID, image relation, event type, optional rating, source, idempotent source key,
canonical sequence and available source timestamp.

Event semantics:

- `rating` appends a score;
- `delete` records the decision and makes the image non-live;
- rating a deleted image appends `restore` and then `rating` atomically;
- `restore` makes the image live without erasing history.

`images.deleted_at` is updated in the same transaction for efficient runtime
queries, but is a projection of the event history rather than a competing
truth. The current score is the latest effective rating after the last
lifecycle boundary. Rating count and average are derived from rating events;
live rankings exclude deleted images.

`current_image_reviews`, `image_review_summary`, `image_reviews` and
`deleted_images` are read-only views. The latter two preserve legacy query
shapes only. No repository may write to them, and all projections can be rebuilt
from `review_events` and canonical image facts.

Review selection adds no stored queue or projection. The active preference is
exposed as `review_prioritize_unrated`; the existing
`workspace_preferences.review_unrated_only` column remains its compatibility
storage and is not an "exclude rated" rule. Candidate order derives from image
identity, `rating_count` and `latest_rating_sequence` in the existing review
summary view. The dormant `review_max_attempts` column remains schema
compatibility only and is absent from the active application/API contract.

## 4. Image and generation provenance

A generation and each output image have separate stable identities. Existing
UIDs survive imports. New historical images and generations receive
content-derived identities; file paths are deliberately excluded from identity.

Generation provenance may include raw sidecar metadata, workflow content and
hash, normalized prompts, checkpoint, LoRAs and ordered sampler stages.
Enriching an existing generation does not replace its source, lifecycle,
ComfyUI prompt ID, timestamps or occupied output slots.

The ComfyUI graph remains the render source of truth. Raw payloads are retained
for provenance and future parsing; application queries use normalized fields.

## 5. Arena and Curation

Arena facts relate `left_image_id`, `right_image_id` and `winner_image_id`.
The match and its generated rating events commit in one canonical transaction.
Fair rotation is derived from immutable match order: the repository returns
each pool image's latest match ID plus all played directions. No cooldown table
or persisted pairing queue is added. Directed reverse matches remain possible
only after the involved images rotate behind older eligible candidates.

Generation lifecycle polling likewise adds no persisted queue. Active work is
the bounded set of native generations already in `prepared`, `submitting`,
`submitted` or `running`. Normalized recovery reasons remain in the existing
generation metadata, and collected outputs remain canonical `images` rows.

Curation relates one image to an optional set key. A filesystem move happens
outside the SQLite write transaction. After a successful move, current image
paths and the assignment update atomically. A database failure causes a
best-effort filesystem rollback; rollback failures are separately visible.

Sidecars are optional for already-canonical images. Review, Top/Worst, Arena,
Curation and Delete therefore work for canonical PNGs without sidecars.

## 5.1 Prompt catalog revisions

The canonical prompt catalog preserves authored material independently
of whether it has already produced an image. A stable prompt component owns
immutable prompt revisions. Each revision owns ordered positive and negative
atom usages.

### Stable catalog standard and calculated candidate

An immutable component revision represents one exact catalog recipe, including
its ordered positive and negative atoms and their standard weights. Keeping
weight on that revision is therefore correct. Weight is nevertheless not part
of atom identity: the same atom used at `0.8`, `1.0` and `1.2` remains one atom.
Changing an atom's semantic content creates a different atom.

The current catalog is intended to expose exactly one global standard for each
stable component identity. It is the revision referenced by the newest
append-only promotion event, not necessarily the numerically latest revision.
Revision 1 of a new component is promoted as a provisional initial standard;
the v14-to-v15 upgrade promotes each existing component's highest revision as a
provisional `migration_baseline`. APIs therefore expose both `current_revision`
and the historically highest `latest_revision`.

A temporary Playground or catalog-content change is a candidate and, after
generation, an observation. It does not immediately change the catalog. If an
exact observed variant later satisfies the versioned stability and promotion
policy, automatic reconciliation reuses or appends the immutable revision for
that complete recipe, including its weights, then appends a promotion event.
Earlier revisions remain bound to their historical images. Display name, tags
and notes remain mutable metadata and continue to take effect immediately.

The product model distinguishes the four Generator choices plus one analytical
comparison:

- the current stable or provisional catalog variant selected by promotion;
- the latest manual catalog variant, regardless of generation or promotion;
- a calculated optimized variant: a weight-only candidate derived from the
  stable recipe and allowed to be unobserved as an exact combination;
- the next useful test: a stable-recipe weight candidate selected to reduce
  uncertainty rather than merely maximize the estimated score;
- the best observed variant remains visible analytical context but is not a
  separate Generator choice.

The Generator offers `Stable`, `Catalog test`, `Calculated` and `Next test`
independently for the eleven normalized prompt groups. Each selection
replaces only that group's atoms in the ordinary editable Generator state. A calculated candidate remains derived guidance until
explicitly materialized and then generated. Promotion is initiated
automatically after a successful Review, Delete or Arena transaction, but
remains explicit as an append-only fact recording the previous revision,
evidence frontier, policy/model version and reason. Promotion failure does not
undo the canonical review; it is logged, returned as `promotion_pending` and
remains idempotently reconcilable.

The `prompt-guidance-v1` policy requires five independent images for a stable
exact variant. Repeated reviews contribute evidence but never increase image
support, and deletes remain negative evidence. Conservative lower-bound score
precedes expectation, average and support. A challenger needs a `0.02`
lower-bound advantage unless the current standard is provisional or no longer
sufficiently supported. Evidence is global to the component rather than split
by checkpoint or surrounding prompt groups.

Calculated guidance may change only the weights of the promotion-selected
stable ordered atom list. Each atom uses observed supported weights plus `0.05`
intermediate values within supported bounds; extrapolation, atom substitution,
insertion, removal and reordering are forbidden. An anchor needs three
independent images and interpolation needs two supported anchors. Effects are
shrunk against the
component baseline and combined as a mean logit effect. The next test uses
`mean + 1.645 * standard_deviation`, may alter several weights, differs from the
current and optimized recipes, and is found without persisting a Cartesian
product.

Schema v15 adds normalized `prompt_component_candidates` and their atom usages,
exact prompt groups and atom usages per generation, and append-only
`prompt_component_promotions`. Each generation group records its component,
source revision and optional candidate. Draft and submission validation proves
that those groups render to the submitted total prompt before all generation
facts are committed atomically. The present `atom_learning_stats` projection
and token analytics remain insufficient by themselves; any new score projection
is derived and rebuildable, and no full prompt Cartesian product is stored.

Historical source attribution is recovered only when stored revisions can be
partitioned exactly into the final rendered prompt. Ambiguous legacy records
remain unknown and do not contribute component guidance. The v15 transition
uses the normal backup/new-output/validation workflow and preserves images,
rendered prompt snapshots, reviews and stable identities.

The v15 runtime tables are canonical facts rather than a score cache:

- `prompt_component_candidates` and candidate atom usages retain explicitly
  selected manual or calculated recipes without turning them into revisions;
- generation prompt groups and atom usages retain the exact component, source
  revision, optional candidate, role, order and weight submitted for each
  generation;
- `prompt_component_promotions` is append-only and makes the newest event's
  revision the current catalog standard while preserving the prior revision,
  evidence frontier, policy version, reason and measurements.

Schema v16 adds `prompt_component_manual_variants` as an append-only authored
selection history. It points at deduplicated candidate recipes but is a
separate fact: the latest manual variant remains queryable after generation,
review or promotion, may equal the current stable revision, and is never
replaced by a calculated or discovery candidate. The v15-to-v16 backfill
records only candidates explicitly stored as `manual`; missing historical
intent is not inferred.

The read repository derives observed variants and atom-weight evidence from
these facts. Guidance candidates are not persisted until explicitly selected,
and no Cartesian product or mutable score authority is stored. The explicit
`prompt-promotions audit|reconcile` maintenance command repairs pending
promotion work; runtime startup never upgrades or reconciles silently.

Display name, tags and notes remain mutable catalog metadata.

`positive_text` and `negative_text` remain immutable renderer-produced
snapshots for provenance and compatibility. They are not writable catalog
input. `PromptRenderer` is the single formatting boundary: weight `1.0` is
rendered without explicit syntax and other weights use deterministic syntax.

A prompt composition references concrete revision IDs. A generation references
the composition/revisions it used and also stores the exact rendered positive
and negative prompt snapshots. Catalog evolution therefore cannot reinterpret
historical generations. Deleting from the UI archives an item; it does not
destroy revisions or historical relationships.

`PromptCatalogService` owns catalog use cases through an injected repository;
SQLite and stable-ID generation remain technical adapters. Playground preview
selection and rendering now consume exact catalog revisions and retain their
UIDs in each draft. A manual draft edit changes only its structured copy. It
does not create or mutate a revision. Preview and submission use the same
server-side renderer. The reviewed browser payload carries ordered typed
component/revision bindings; confirmation reloads those exact immutable
revisions, including explicitly selected archived history, and rechecks the
current content policy before persistence. It never upgrades an older revision
to the component's latest revision. Playground submission uses the native
`GenerationService`, preserves flattened structured usages, exact rendered
snapshots and selected revision IDs, and does not dual-write legacy generation
state. Those facts support exact generation provenance and broad
component-scoped evidence. A future per-component promotion flow must preserve
an explicit candidate source binding when simultaneous group edits would make
that binding ambiguous.

Legacy prompt migration is explicit:

```text
python -m comfyreview legacy-prompts audit
python -m comfyreview legacy-prompts import [--backup-dir PATH]
```

The audit binds both databases by SHA-256 and reads the source in SQLite
read-only mode. The import revalidates the snapshot, creates a backup and
writes the complete accepted set in one transaction. It is idempotent, retains
unused items and never mutates the source database.

Historical generation-to-composition completion is a separate explicit step:

```text
python -m comfyreview legacy-compositions audit
python -m comfyreview legacy-compositions import [--backup-dir PATH]
```

The version-2 audit considers every immutable canonical revision and recognizes
complete positive/negative prompt-atom sequences. Historical compositions may
contain any non-empty, ordered subset of catalog slots; the importer does not
require all catalog kinds to be present. A slot is accepted only when its
revision match is unique and consistent. Additional historical prompt text is
retained solely in the unchanged generation snapshot and is classified as a
draft override rather than invented as a component or revision.

Results are classified as `already_exact`, `exactly_reconstructable`,
`reconstructable_with_draft_override`, `ambiguous`, `insufficient_evidence` or
`conflict`. Both reconstructable categories may be linked. Ambiguous or
incomplete evidence never creates a guessed relationship. Composition UIDs are
derived from ordered slot, position and revision-UID tuples; paths are not
involved. Audit format version 2 prevents the discarded fixed-slot report from
being imported.

Earlier live composition-import counts and their unresolved cases are retained
solely in the [archivierten Canonical-DB-Betriebsnachweisen](archive/canonical-data-operator-evidence-2026-10-01-to-07.md). They are
historical source observations, not current database inventory, schema
invariants or reconstruction defaults.

The v14 legacy-provenance recovery completes retained generation relationships
from three explicitly labelled evidence
classes: the embedded immutable generation recipe, unique exact snapshot
matches and a reviewed curation manifest. The commands are intentionally
separate:

```text
python -m comfyreview legacy-provenance audit [--curation PATH]
python -m comfyreview legacy-provenance recover --output NEW_DATABASE
```

The report is bound to the source database and optional curation file by
SHA-256. `recover` refuses an in-place target, copies the source through the
SQLite backup API, applies all revisions, composition links and evidenced LoRA
bindings in one
transaction, validates the result and only then installs the requested output
file. Existing revision UIDs and contents are untouched. Recovered historical
revisions are numbered below the pre-existing latest revision; recognizable
variants become prior revisions of their real component and no remainder
component is created. Rendered generation prompts remain
immutable unless the reviewed curation contains an explicit, source-hash-bound
fragment correction; recovery then creates a new normalized prompt row and
relinks only the named generations. Review facts, image identity and
content-level state are not rewritten.

The implementation separates embedded-recipe evidence, unique exact matches
and reviewed semantic reconstruction. **Dated operator totals and item-specific
repairs** are retained in the [archivierten Canonical-DB-Betriebsnachweisen](archive/canonical-data-operator-evidence-2026-10-01-to-07.md);
they must not be treated as current runtime counts or universal validation
rules. Any remaining unknown or ambiguous provenance in a newly audited
database is reported rather than guessed.

## 5.2 Current catalog composition and normalization

The selectable prompt-kind order is `character`, `scene`, `atmosphere`,
`lighting`, `outfit`, `accessory`, `pose`, `expression`, `framing`,
`camera_angle`, `optical_effect`. Character is mandatory; every other group
may be off. `modifier` is accepted only as old migration/provenance input and
can never have `catalog_role = 'catalog'` in a normalized result.

Every retained image owns exactly one selected versioned catalog composition.
The immutable generation keeps its original complete positive/negative prompt,
generation composition, exact group snapshots and renderer provenance. Reads
that mean “current catalog meaning” use the image composition instead:
Playground handoff, scopes, analytics, rating atom attribution and automatic
promotion. Exact generated candidate atoms remain usable only while the
current component/revision still matches that original generation group.
Composition selection lookup accepts both authored composition identities and
current image-catalog composition identities. Aggregate Analytics cards use
the first ranked best image identity for prompt and LoRA handoff, preserving
the exact image-level composition and ordered LoRA revisions independently of
any render-parameter action.

Quality/anatomy negatives and content profiles are immutable global policy
revisions, not selectable catalog components. A generation records the exact
policy revisions used. Rendering deduplicates canonical text within each scope;
an explicitly selected component atom and its weight win over a global
duplicate. Global policy atoms are not optimizable catalog evidence.

Catalog cleanup is an explicit offline workflow:

```text
python -m comfyreview catalog-normalization audit
python -m comfyreview catalog-normalization rebuild --output PATH [--replace]
```

Audit reads the source transactionally, inventories all components, revisions,
atoms, live/deleted images and original prompts, and writes a hash-bound report
plus an ignored editorial mapping draft. Audit never splits prompt text,
chooses catalog alternatives, creates target components or marks source/image
rows as reviewed. Those decisions belong exclusively to the subsequent manual
editorial pass. Rebuild requires every source
component and live image to be marked reviewed, rejects unsupported kinds or
duplicate image groups, rejects every Non-Character `keep` decision, and
requires every replacement to use a new component UID with exactly revision
1. All ten Non-Character groups must have target components referenced by
reviewed source decisions; unresolved `or` alternatives, archived
selectable entries and `modifier` are validation failures. The
validator checks completeness, groups, UIDs, structural references and
hash bindings, **not whether the editorial semantic interpretation is
factually correct**. Marking a mapping `reviewed` cannot prove that
its prompts were split or classified appropriately. The operator must
review that meaning separately before accepting the rehearsal and any
cutover. The mapping checksum is validated in addition to its audit
and source hashes. It locks and re-hashes the source, upgrades only a
temporary copy, and writes a distinct output database. `--replace` installs
that database atomically after schema and cutover validation. Per the explicit
operator decision for this one workflow, it creates no additional backup.

Old Non-Character components survive only with
`catalog_role = 'generation_provenance'` when a retained generation still
references them through its immutable authored composition or structured
generation groups. They need no selectable promotion, are excluded from all
catalog lists and cannot be resolved through the authored-composition handoff
fallback. Unreferenced old components, revisions, candidates, promotions and
compositions are removed. Every retained generation is bound to the active
quality policy and the content profile selected by its effective content
level.

The first real output is an acceptance rehearsal, not a promotion candidate.
It is selected with `COMFYREVIEW_DATABASE` and served on a separate port by
`python main.py`, so manual checks traverse the ordinary schema lifecycle and
runtime repositories. Ratings or other acceptance writes intentionally taint
that file. After explicit acceptance, the operator stops the canonical app and
runs the same hash-bound rebuild again with a new output name and `--replace`;
only that untouched fresh result may replace the source.

Before reset, current effective ratings of live images become canonical atom
and render baselines. Identical retained atoms map directly; explicit 1:1 or
synonym mappings deduplicate support per image; split, rewritten and new atoms
receive no inferred prior. Then deleted images and orphan-only facts are
removed, Review/Arena/Curation and the clock are reset, rating-derived
candidates/promotions are removed, and projections are initialized from the
baselines. Baseline support never counts as a new independent image for
promotion because promotion reads only post-reset `review_events`. New reviews
add to the projections without mutating the baseline facts.

Character components are excluded from semantic cleanup. Rebuild validation
compares their internal IDs, UIDs, archive states, revisions, atom identities,
weights, complete promotion history, selected standards, manual candidates and
manual-variant bindings. No fixed per-character revision count is imposed by this documentation:
source-specific revision counts (including the earlier Aiko snapshot) are
recorded in the [archivierten Canonical-DB-Betriebsnachweisen](archive/canonical-data-operator-evidence-2026-10-01-to-07.md).
Rebuild acceptance compares the character's entire existing revision history
against the audited source instead of enforcing an old inventory count.

## 5.3 Workspace preferences, content, profiles and LoRA usage

Schema v8 stores one typed workspace-preference row plus an ordered list of
visible Curation sets. Preferences affect presentation/session defaults; they
do not rewrite review or curation facts. Generation-profile rows and their
ordered LoRA relations remain dormant migration compatibility in v14. They are
not read by the active runtime, Settings, Playground or V2 API.

New generations persist the concrete LoRA stack used after validation and
compilation. Capability discovery supplies available names, while the
`WorkflowCompiler` alone inserts the ordered loader chain into the active Blueprint v4.
The ComfyUI provider still receives only a compiled graph. A normalized
generation LoRA must have at least one non-zero model or CLIP branch connected
to a sampler-consumed graph path and at least one exact trigger from its bound
revision in the matching final prompt scope. Historical `loras_json` is
retained as raw provenance, including disconnected or triggerless nodes; the
explicit audit/recovery path normalizes only fully evidenced values.

Schema v9 adds an ordered content-level relation and validated image width and
height fields. The active catalog create/edit path now writes exactly one
canonical `content_level_*` marker to component metadata without another
schema change. **Historical components need not yet carry that marker**:
reads prefer the canonical level, otherwise accept recognized legacy aliases,
or default to `standard` if no classification exists. Conflicting
canonical markers, or conflicting legacy levels without a canonical marker,
are rejected. The repository exposes the resulting typed level and removes
canonical markers from descriptive tags. The shared visibility predicate
gates ranking, review candidates, Arena pairs, Scope facets, Analytics,
Catalog evidence and Playground from the immutable generation-level
snapshot plus an optional image override. Later catalog edits
therefore never change historical image visibility implicitly.

Schema v10 makes stable LoRA identity and generation snapshots canonical.
Schema v14 makes the immutable trigger revision the classification owner.
Newly discovered provider filenames are not usable until an available revision
has trigger atoms and a typed content level. Every retained normalized usage
snapshots stable UID, exact revision, resolved filename and revision level. Its
inferred level is the maximum of all authored component levels and only those
LoRA snapshots whose graph branch and scoped trigger were both evidenced.
Catalog edits affect new generations and do not silently rewrite history.

Schema v12 gives those definitions immutable functional revisions. Triggers
use the same canonical weighted atom model as Prompt Catalog content. Changing
triggers or default strengths appends a revision; display name, tags and notes
remain mutable metadata. Generation requests carry stable LoRA and revision
UIDs, while the server resolves the provider filename. Historical usage
without proof remains only in raw graph provenance; v14 recovery removes it
from the normalized `generation_loras` relation.

Schema v13 moves the current Generator controls into normalized canonical
relations. Scalar render/seed settings have one singleton owner; prompt rows
store role, mode and exact component/revision references; ordered LoRA rows
store exact definition/revision references and milli-unit strengths. Saves
replace all three parts in one transaction. The previous JSON state is not a
runtime fallback and can be read only by the explicit v12-to-v13 copy
migration after strict `generator_v2` validation.

Schema v14 moves the typed LoRA content level onto `lora_revisions`. The old
definition field is retained only so older copy migrations remain readable.
New generation rows require an exact revision and snapshot its level only after
the compiled graph and final scoped prompt prove real use. The offline
provenance recovery applies the same rule to history and refuses promotion
unless every active prompt atom and every retained LoRA binding is unambiguous.

Historical v12-to-v14 promotion counts and its evidence-bound acceptance
results are documented in the [archivierten Canonical-DB-Betriebsnachweisen](archive/canonical-data-operator-evidence-2026-10-01-to-07.md).
They do not establish the version or content of a current private runtime
database. Schema and validation semantics above remain code contracts.

Historical reclassification is a separate two-step operation: preview returns
the affected generation/image counts and catalog revision, and apply requires
that exact revision in one transaction. It rebuilds every snapshot from its
bound immutable revision rather than copying the current catalog level across
history. A stale revision or any write failure rolls the operation back.
Existing manual image overrides remain untouched.
Manual changes append an immutable event and update or remove the current
projection atomically. The effective level is the override when one exists,
otherwise the inferred generation level.

Prompt-catalog repair uses the separate `content-levels audit/recover`
workflow. Its versioned curation binds every
relevant source component UID and each editorial decision to the latest
revision UID and content hash. Source-specific row counts are archived in the
[archivierten Canonical-DB-Betriebsnachweisen](archive/canonical-data-operator-evidence-2026-10-01-to-07.md).
The audit binds database and curation hashes and previews component,
generation and image transitions. Recovery copies the source into a new
database, updates canonical markers and generation snapshots, and removes
graph-inactive LoRA selections from the normalized relation in one short
transaction. Raw workflow provenance, source data and manual overrides remain
unchanged. The output is validated before promotion; backup and promotion stay
explicit operational steps.

Schema v11 geometry is deliberately derived. `PngHeaderDimensionReader` reads
the source dimensions behind a filesystem provider boundary. Aspect format is
the smallest logarithmic ratio deviation; output class uses the nearest nominal
short edge among the stable 720, 1080 and 2160 compatibility values, with a
higher-class tie break. The highest class targets the complete 4x AnimeSharp
dimensions for the classified format. Approximate matches are recorded without
rewriting files. The explicit rebuild scans first and performs one short atomic
projection replacement afterward.

## 6. Audited historical output import

Historical output migration has two explicit steps:

```text
python -m comfyreview legacy-output audit
python -m comfyreview legacy-output import [--backup-dir PATH]
```

The audit fingerprints the canonical database plus PNGs, sidecars and workflow
graphs. The importer validates the report structure and UID assignments, then
recomputes hashes immediately before any write. Missing files, changed content,
unknown samplers, partial graphs and UID/path/output-slot collisions abort the
whole import. PNGs without sidecars are reported separately and are not
invented as canonical records. Source PNGs and sidecars are never modified.

The accepted import writes all provenance and sampler stages in one SQLite
transaction after creating a backup, then refreshes the geometry projection
outside that transaction. Canonical readers use a genuine
SQLite `mode=ro` connection.

## 7. Audited legacy feature import

Ratings, Arena and Curation use their own audit/import workflow:

```text
python -m comfyreview legacy-features audit
python -m comfyreview legacy-features import [--backup-dir PATH]
```

All source databases are opened read-only and bound to the report by SHA-256.
Legacy paths are used only to resolve an existing canonical image UID; no UID is
derived from a path. Existing canonical v3 reviews are deduplicated against
matching source facts. Ambiguous or contradictory mappings block the import.
Historical missing images and dependent facts are reported as orphans.

The importer is idempotent, validates aggregate parity and writes ratings,
matches and assignments in one canonical transaction. Observed source counts
are operational control values, not hard-coded schema expectations.

## 8. Backup, rollback and restore

Every import workflow completes validation before opening the write
transaction and creates a SQLite backup before the first write. All accepted
facts for that import then commit in exactly one transaction. A fresh audit and
new backup are required after each preceding import because the canonical hash
has changed.

On an ordinary exception the transaction is rolled back first. The production
database is validated after rollback and is not overwritten merely because an
exception occurred. A physical restore is attempted only when validation fails,
an out-of-transaction structural change took effect or the commit state cannot
be established. Restore errors remain distinguishable from the original error.

Reports, backups and runtime databases are local artifacts ignored by Git.

## 9. Legacy databases during transition

| Legacy database | Current treatment |
| --- | --- |
| `ratings.sqlite3` | read-only review import source; not Review runtime truth |
| `arena.sqlite3` | read-only Arena import source; not Arena runtime truth |
| `curation.sqlite3` | read-only Curation import source; not Curation runtime truth |
| `images.sqlite3` | historical feature-import evidence only |
| `prompt_tokens.sqlite3` | historical projection retained only for explicit maintenance |
| `prompt_ratings.sqlite3` | historical derived statistics retained only for explicit maintenance |
| `combo_prompts.sqlite3` | historical eager projection retained only for explicit maintenance |
| `playground.sqlite3` | audited prompt-import source only |
| `mv_jobs.sqlite3` | historical worker/job database; no runtime consumer |

Legacy DDL remains centralized in
`comfyreview.repositories.sqlite.legacy_schema`. Legacy paths are loaded through
`LegacyMigrationSettings`, which is not part of the application container.
Normal runtime startup neither opens nor initializes these files. Known
additive changes require the explicit `python -m comfyreview legacy-db upgrade`
command.

## 10. Canonical analytics queries

Die früher hier eingebetteten **Schema-v9-Live-Zahlen, Upgrade- und
Rehearsalberichte** stehen ausschließlich im
[historischen Operatorprotokoll](archive/data-schema-v9-operator-report.md).
Sie sind **keine** aktuelle Statistik der privaten ComfyReview-Datenbank.


Render guidance reads canonical generations, ordered sampler stages, images
and append-only `review_events`. It aggregates all rating/delete evidence once
per stable image ID, so several events may change weights and averages while
support thresholds still count one independent image. Central content-level
visibility is part of the repository query.

The active render tuple is checkpoint, sampler, scheduler, Steps, CFG and
Denoise. Seed, LoRAs, format/orientation and resolution class are not optimizer
dimensions. Exact observed tuples and marginal values are derived on request.
The `render-guidance-v1` model and representative image IDs are rebuildable
read models; no forecast, score or candidate is stored. This feature therefore
does not change schema v11 and requires no migration.

Prompt combinations are identified by canonical `prompt_composition_id` and
remain distinct from render discovery. No runtime path reparses legacy
`combo_key` values or materializes possible prompt/render cross-products.

The Card Battler is being developed **now as a ComfyReview POC**.
An [earlier target plan](archive/card-battler-target-2026-10-02.md) is
historical and does not prescribe future card persistence.
[Card POC](pocs/card-battler.md).

**ComfyReview is still evolving toward Character Chronicles**, but this
current canonical SQLite v18 design is not a compulsory permanent schema
for the eventual game. The imported Chronicle concepts include some
**abandoned earlier schema 47–58/Guardian architecture**; their tables,
migrations and persistence authority are **not** part of the current
ComfyReview database and must be independently re-evaluated.
[Decision Policy](DECISION_POLICY.md).
