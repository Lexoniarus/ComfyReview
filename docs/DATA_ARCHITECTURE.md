# ComfyReview Data Architecture

Status: migration direction, not final physical schema, 2026-09-28.

This document records the persistence principles that must be preserved while
ComfyReview is consolidated from multiple SQLite files into one canonical
runtime database.

## 1. Current legacy database roles

The current repository and historical files show these roles:

| Legacy database | Role | Target treatment |
| --- | --- | --- |
| `playground.sqlite3` | reusable character/scene/outfit/etc. prompt components | migrate as canonical domain data |
| `ratings.sqlite3` | raw review/rating history and generation context | migrate as canonical review/image facts |
| `arena.sqlite3` | pairwise image decisions | migrate as canonical Arena facts |
| `curation.sqlite3` | image -> curation set assignment | migrate as canonical curation facts |
| `prompt_tokens.sqlite3` | per-rating/run expansion of prompts into atoms | do not blindly copy; rebuild normalized prompt/atom relations |
| `images.sqlite3` | derived per-image aggregate/materialized view | rebuild from canonical data |
| `prompt_ratings.sqlite3` | derived per-atom aggregate | rebuild from canonical data |
| `combo_prompts.sqlite3` | large precomputed combination projection | redesign; migrate only domain-relevant compositions/facts |
| `mv_jobs.sqlite3` | projection job/cursor state | replace with canonical operational job/projection state |

The target runtime does not preserve one SQLite file per concern.

## 2. Source-of-truth rule

A datum must have one authoritative home.

Examples:

- Image generation metadata belongs to the image/generation record.
- A review score belongs to a review event.
- A prompt atom belongs to the prompt vocabulary/membership model.
- Aggregate average score is derived; it is not another independent fact.

No new design may require keeping the same business fact synchronized across
multiple writable databases.

## 3. Stable identities

Use stable integer IDs and/or UUIDs for domain identity.

Paths are mutable attributes:

```text
image_id = 827
png_path = E:/ComfyUI/output/.../image.png
```

If the path changes, `image_id` remains 827 and reviews/comparisons/curation
remain valid.

## 4. Prompt/content components

The legacy `playground_items` concept is useful and should survive in normalized
form.

A component has at least:

- stable ID
- `kind`
- stable key/slug
- display name
- positive text
- negative text
- tags/notes

Kinds may include character, scene, outfit, pose, expression, modifier,
lighting and future compatible categories.

## 5. Prompt compositions

A composition is a real ordered combination of components.

Use a relation such as:

```text
prompt_compositions
prompt_composition_members
```

Do not store every theoretical character x scene x outfit permutation merely
because it is computable. Persist a composition when it is actually generated,
used, curated, explicitly saved or otherwise becomes domain-relevant.

## 6. Exact prompts and atoms

Exact positive/negative prompt text should have stable identity (for example by
hash + canonical text record).

Tokenize an exact prompt once into ordered atom memberships:

```text
prompts
prompt_atoms
prompt_members
```

Do not duplicate the same atom text for every rating event.

The large historical `prompt_tokens.sqlite3` is therefore treated as a legacy
projection/journal, not as the desired canonical shape.

## 7. Images and raw metadata

An image record stores normalized generation fields such as:

- stable image/generation ID
- current PNG/JSON paths
- prompt IDs
- checkpoint/model reference
- seed
- steps
- CFG
- sampler
- scheduler
- denoise
- LoRA/config references as appropriate
- timestamps

Preserve the raw sidecar/workflow payload separately for provenance and future
re-parsing. Raw metadata is not the primary query model.

## 8. Reviews

Model reviews as events/facts, not overwritten image columns.

A review event may represent:

- score/rating
- delete/restore decision if that remains product behavior
- timestamp/session/user context when applicable

Per-image averages, counts and rankings are derived from review events.

## 9. Arena

Arena records reference image IDs:

```text
left_image_id
right_image_id
winner_image_id
```

They do not use mutable JSON/PNG paths as relational identity.

## 10. Curation

Curation references `image_id` and a typed/set key. Moving the underlying file
does not change curation identity.

## 11. Derived statistics

Derived tables/views must be small, purposeful and rebuildable.

Candidate projections:

- image review summary
- prompt atom performance by checkpoint and global scope
- composition performance

Start as SQL views where performance is sufficient. Materialize only after
measurement demonstrates a need.

## 12. Operational state

Background queue and projection cursor state may share the canonical SQLite
file but are operational, not product facts.

Examples:

```text
background_jobs
projection_state
schema_meta
```

They must be safe to rebuild/reset according to documented rules without
corrupting canonical review/image/prompt data.

## 13. Schema versioning

The canonical database has an explicit schema version.

Runtime behavior:

- supported version -> open normally
- older/newer unsupported version -> fail explicitly
- no silent structural repair of arbitrary databases on application startup

Offline migration behavior:

- source database(s) remain unchanged
- backup/source verification first
- create new output database
- migrate inside explicit transactions
- validate counts, relationships and invariants
- produce a migration report
- activate only after user acceptance

## 14. Character Chronicles relationship

ComfyReview should provide a clean image/prompt/review foundation that Character
Chronicles can later reuse or extend.

Character Chronicles-specific concerns such as image descriptions, embeddings,
RAG, campaign/gameplay state and card-battler data are not added to ComfyReview
merely to anticipate future use.

If both products later share one physical database, ComfyReview's core tables
remain independently understandable and Character Chronicles adds explicit
extensions rather than duplicating the same image/prompt/review facts.
