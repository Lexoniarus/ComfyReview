> [!CAUTION]
> **ARCHIVED — historical ComfyReview implementation snapshot, not current instructions.** The work-order Problem statement was written before the already-completed schema-v7 implementation. Its imperative steps and old non-goals are not pending work.
> Original: `docs/STRUCTURED_PROMPT_BUNDLES_WORK_ORDER.md`, revision `b248ee5bdd37bc488f8d0680bb655f193e8c4ac6`. The original text below is kept for provenance, including its past-tense and obsolete present-tense statements. For the current state use [Project Status](../../project_status.md), [Data Architecture](../../DATA_ARCHITECTURE.md) and the [Documentation Index](../../README.md).

---

# Work Order: Structured Prompt Bundles

Status: implemented on `refactor/review-boundary`, 2026-10-02.

Clarification, 2026-10-07: this work order correctly separated atom identity
from usage weight and made each immutable component revision an exact weighted
standard recipe. Experimental Playground variants remain drafts or generation
observations until an exact observed recipe is promoted. Evidence-based choice
of the stable standard, calculated optimized variants and promotion were
explicitly outside this historical slice and are tracked in
`REFACTOR_PLAN.md`.

## Purpose

Prompt catalog components such as a character, scene or outfit must be modeled
as ordered collections of positive and negative prompt-atom usages. A component
must no longer derive its internal meaning solely from two opaque prompt
strings.

For example, the stable catalog identity `Aiko` remains the bundle. Its content
revision contains the individual positive and negative usages that together
describe Aiko. Each usage keeps prompt text and numeric weight as separate,
machine-readable values.

The complete positive and negative strings are rendered boundary formats for
display, provenance and ComfyUI submission. They are not the authoritative
editable representation of a catalog revision.

## Problem statement

The canonical generation persistence already parses rendered prompt snapshots
into atoms and stores a membership weight. The revisioned Prompt Catalog and
its current frontend, however, still author `positive_text` and `negative_text`
as whole strings. Playground draft overrides also operate on complete strings.

This split prevents the application from reliably performing elementary prompt
operations such as:

- changing only the numeric weight of one Aiko atom;
- replacing the text of one atom without editing an opaque combined string;
- adding, removing or reordering one positive or negative atom;
- making a temporary Playground variation without modifying Aiko's canonical
  catalog revision;
- preserving an exact structured account of the values used to render a
  generation prompt.

## Target domain model

The implementation must establish the following conceptual structure:

```text
PromptComponent (stable identity, for example Aiko)
    -> PromptRevision (immutable approved catalog content)
        -> ordered positive PromptAtomUsage values
        -> ordered negative PromptAtomUsage values

PromptAtomUsage
    atom text/reference
    numeric weight
    scope (positive or negative)
    position
```

Canonical atom text and the weight of a particular usage are distinct values.
Weight belongs to an occurrence in a revision, draft or generation, never to
canonical atom identity. The same atom may therefore be tested and observed at
different weights without creating another atom. A draft experiment does not
create a catalog revision. If an exact observed variant is later promoted as
the component's stable standard, the complete weighted recipe becomes a new
immutable revision.

Replacing text in a draft must not globally mutate a canonical atom that may be
shared by other components or revisions. It creates or selects the appropriate
atom value for that draft usage. Existing immutable catalog revisions remain
unchanged.

No semantic property-slot system is required by this work order. The ordered
atom usage is the required level of structure.

## Authoritative data and rendering

- Ordered positive and negative atom usages, including their standard weights,
  are the authoritative editable content from which every catalog revision is
  created. Once created, the revision is immutable.
- A dedicated renderer produces deterministic positive and negative prompt
  strings from the ordered usages.
- The renderer owns weight syntax and escaping/formatting decisions. Frontend
  components, routes and the ComfyUI provider must not recreate those rules.
- An unweighted/default usage is represented numerically with the canonical
  default weight, even if the rendered boundary string omits explicit weight
  syntax.
- Generation provenance retains the exact rendered positive and negative
  snapshots submitted to ComfyUI. Structured generation membership must remain
  sufficient to recover the atom text, scope, order and weight that produced
  those snapshots.
- Parsing combined text may remain an explicit import or compatibility
  operation. It must not remain the normal editing model.

## Catalog requirements

- Creating or revising a component accepts ordered structured atom usages.
- A content change appends an immutable revision; it never rewrites an older
  revision.
- Name, tags, notes and archive state retain their existing metadata semantics.
- Positive and negative collections are independent and preserve their order.
- Atom text, weight, scope and position are validated before persistence.
- Persistence uses stable identities and normalized relations rather than
  duplicating complete atom payloads for each rating or event.
- The old whole-string revision data is migrated through an explicit,
  versioned, backup-before-write migration. Runtime startup must not silently
  perform the conversion.
- Migration must preserve component identity, revision identity and number,
  composition membership, ordering, positive/negative scope and the rendered
  meaning of existing revisions.
- Ambiguous or unsupported legacy prompt syntax must be reported rather than
  silently reinterpreted.

## Playground requirements

Playground is in scope because it is the main working surface for temporary
prompt variation.

- Selecting Aiko or another catalog component loads a structured copy of the
  selected immutable revision into the draft.
- The user may change an atom's text or weight, add or remove atoms, and reorder
  atoms in that draft.
- Draft edits do not update the selected catalog component or revision.
- Resetting a component restores the selected catalog revision's atom usages.
- Preview and submission use the same backend renderer so the shown prompt and
  submitted prompt cannot diverge.
- A generation request records the selected revision identities, the structured
  draft values actually used and the exact rendered prompt snapshots.
- Composition selection and prompt override behavior must be redefined in
  terms of structured draft values rather than raw string replacement.

This work order does not require a durable experiment or Try aggregate. A
Playground draft is sufficient for temporary variation at this stage.

## Frontend requirements

The Catalog and Playground surfaces must represent positive and negative atoms
as editable ordered rows instead of relying on one textarea per scope.

Each row must provide at least:

- a text control for the prompt content;
- a numeric weight control;
- its positive or negative context;
- controls to add, remove and reorder the row.

The UI must also show a read-only rendered prompt preview. The preview is an
explanation of the resulting ComfyUI input, not a second editable source of
truth.

Frontend implementation must follow the existing V2 contracts:

- native ES modules;
- one shared frontend API module;
- no direct `fetch()` in views or components;
- dynamic values rendered as text or attributes;
- lifecycle ownership and disposal for listeners and in-flight requests;
- JSDoc contracts and `checkJs` validation;
- accessible labels, keyboard operation, validation messages and responsive
  behavior.

## API and application boundaries

- HTTP payloads expose explicit structured atom usages rather than encoding
  them only inside strings.
- Routes translate payloads and responses but do not parse prompt grammar or
  apply catalog rules.
- Application services coordinate catalog revisions and Playground drafts.
- A focused domain renderer converts structured usages into prompt strings.
- Repositories persist structure and revisions but do not own rendering or
  Playground orchestration.
- `WorkflowCompiler` continues to receive already-decided rendered positive and
  negative prompt values. It does not become a prompt editor.
- `ComfyUiProvider` remains unaware of bundles, atoms, weights and catalog
  roles.

## Analytics compatibility

This work must preserve the ability to query evidence by canonical atom text,
positive/negative scope, model context and numeric weight. Consumers must not
need to reparse a rendered token string to distinguish text from weight.

No new rating algorithm is required here. Existing aggregate behavior may be
retained where compatible, but the structured facts needed by later analytical
work must not be discarded.

## Required implementation order

1. Define the structured domain values, invariants and deterministic renderer.
2. Define the versioned schema change and a non-destructive migration/audit
   strategy for existing prompt revisions.
3. Change catalog repository and application contracts to structured revision
   content.
4. Change API V2 request and response contracts.
5. Replace Catalog whole-string editing with ordered atom rows and a rendered
   preview.
6. Move Playground selection, draft editing, preview, reset and submission to
   structured atom usages.
7. Verify generation provenance and analytics retain exact atom/weight facts.
8. Remove obsolete whole-string authoring paths only after migration and all
   consumers have cut over.
9. Update architecture, data, frontend and user-facing documentation to the
   implemented state.

## Acceptance criteria

- A catalog component is loaded through its public API as ordered positive and
  negative atom usages with separate text and numeric weight.
- Creating a component and appending a revision never require callers to build
  weighted prompt strings.
- Changing only a Playground weight produces a new draft value while retaining
  the atom text and leaving the source revision unchanged. Saving a deliberately
  chosen weighted recipe as the new catalog standard appends a revision.
- Changing only atom text leaves weight, scope and order intact unless the user
  explicitly changes them.
- Add, remove and reorder operations have deterministic rendered results.
- Catalog save creates an immutable revision and preserves all older revision
  content.
- Playground edits are isolated from canonical catalog content.
- Playground preview and the submitted ComfyUI prompt are byte-for-byte
  consistent after rendering policy is applied.
- Persisted generation facts retain exact text, weight, scope and order for all
  submitted atoms as well as the rendered snapshots.
- Existing catalog and composition identities survive the explicit migration.
- Unsupported legacy syntax blocks or reports the affected migration item; it
  is not silently flattened into a different meaning.
- Behavior tests cover successful editing/rendering, validation failures,
  immutable revision behavior, draft isolation and migration rollback.
- Frontend tests cover atom-row editing, positive/negative separation,
  reordering, reset, validation, preview and submission payloads.
- Architecture checks continue to enforce repository, service, route,
  provider and frontend API boundaries.
- The complete shared quality gate passes before the slice is considered
  implemented.

## Explicit non-goals

- automatic optimization of Aiko or any other component;
- promotion of a Playground variation into a new canonical baseline based on
  ratings;
- experiment/Try lineage, hypotheses or controlled A/B evaluation;
- causal attribution of an image rating to one changed atom;
- semantic slots such as eye color, hair style or clothing property;
- Character Chronicles gameplay, RAG or embeddings;
- changing ComfyUI transport or workflow-provider responsibilities;
- materializing every possible prompt combination.

Those capabilities may build on the structured representation later, but they
must not enlarge this historical work order. Prompt-variant guidance and
evidence-based promotion are now tracked as a separate schema-v15 slice in
`REFACTOR_PLAN.md`. That follow-up treats text changes as new atom identity,
weight changes as use of the same atom, manual component recipes as candidates,
and the newest auditable promotion as the catalog standard.

## Implemented result

Schema v7 adds `prompt_revision_atom_usages`, relating each immutable revision
to a canonical atom by positive/negative scope, ordered position and
`weight_milli`. The explicit backed-up v6-to-v7 migration preserved all 729
component/revision identities and renderer-produced snapshots while creating
4,061 validated usages. Rehearsal and live validation both completed with an
integrity-valid database and no foreign-key violations.

Catalog V2, Playground draft preparation and generation submission now use
structured arrays. The server validates the selected revision UIDs and renders
the final positive/negative snapshots centrally; the browser cannot submit an
arbitrary workflow graph or treat a free-form final prompt as canonical truth.
The Catalog and Playground atom editors own their listeners, support add,
remove, reorder and reset, and pass `checkJs`, lint and focused behavior tests.

The combined-string parser remains only where historical migration or the
legacy HTML form contract explicitly requires it. It is not a writable
application or repository contract.
