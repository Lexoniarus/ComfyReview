# Frühere Canonical-DB-Betriebsnachweise – 1. bis 7. Oktober 2026

**Dokumentklasse:** `HISTORICAL_LOG` · **Rolle:** wortgetreue archivierte
Operator-/Datenbestandsangaben, keine heutige Datenbankinventur, keine
aktuellen Laufzeit-Invarianten oder Freigabe für Datenbankaktionen.

Die folgenden Passagen stammen aus der früheren Fassung von
[`docs/DATA_ARCHITECTURE.md`](../DATA_ARCHITECTURE.md) und
[`docs/ARCHITECTURE.md`](../ARCHITECTURE.md), im Dokumentationsstand von PR #8 bei Commit `98d8bcf` enthalten
und in den anschließenden Korrekturen am 9. Oktober 2026 aus den
aktiven Architekturtexten ins Archiv übertragen.
Die Absätze werden hier als historische Angaben **unverändert**
bewahrt. Sie belegen allein die damaligen Aussagen und beziehen sich
auf frühere lokale Datenbanken, die im Repository nicht mitgeliefert werden.
Die übrigen Operatorprotokolle stehen im
[archivierten Projektstatus](project-status-log-2026-10-09.md) und im
[Refactor-Slice-Verlauf](refactor-slice-history-2026-10-09.md).
Für aktive Datenverträge zählt die [Datenarchitektur](../DATA_ARCHITECTURE.md);
der aktuelle private DB-Stand muss separat nachgewiesen werden.

## Legacy composition completion, 2026-10-01

The completed 2026-10-01 live run linked 363 of 379 generations: 29 rendered
exactly from their recovered memberships and 334 retained additional historical
draft text in the canonical prompt snapshot. Sixteen generations remain
unlinked: two have ambiguous expression evidence and fourteen have no
sufficient catalog evidence. There were no conflicts. These are observed data
results, not hard-coded importer expectations.

## Legacy provenance recovery, 2026-10-06

The reviewed 2026-10-06 recovery covered 389 generations and 384 active images.
Against the pre-recovery runtime source it classified 119 embedded recipes,
no remaining exact enrichments and 203 reviewed reconstructions, created 117
historical revisions plus 12 archived recovered detail concepts, relinked 192
generations and applied 18 hash-bound prompt corrections. The validated output
was promoted only after preserving the prior runtime database as a backup and
was then served again on the LAN runtime.

No ordinary scene, outfit, pose, expression, lighting or framing block remains
unidentified. Seventeen images retain prompt-side LoRA trigger atoms that are
owned by their normalized LoRA provenance rather than prompt-component
memberships. The earlier combined modifier and lighting revisions remain
historical source/provenance facts until the catalog-normalization cutover;
they are not valid normalized target components. Six active and two deleted
Hina generations had their missing expression/lighting separator restored and
were linked to separate historical expression and lighting revisions. All 18
formerly structural active-image residuals are therefore resolved; the only
remaining positive atoms outside normal component memberships are attributable
LoRA triggers. These are curated data facts, not runtime heuristics or importer
constants.

## Character revision check – Aiko (historical source-specific invariant)

Character components are excluded from semantic cleanup. Rebuild validation
compares their internal IDs, UIDs, archive states, revisions, atom identities,
weights, complete promotion history, selected standards, manual candidates and
manual-variant bindings. When Aiko exists, exactly 24 revisions are required.

## Canonical v12-to-v14 promotion, 2026-10-07

The live 2026-10-07 promotion copied the v12 runtime through v13 and v14 into a
new database before replacement. Its bound audit covered 414 generations and
393 active images, reported zero unattributed or over-attributed atoms and zero
ambiguous LoRA bindings, and retained 19 exact trigger-evidenced LoRA usages.
It removed 832 unsupported normalized usage rows while preserving the stored
raw graphs. Independent validation reported `integrity_check = ok`, no foreign
key errors, no retained null LoRA revision and complete editable handoffs for
all 393 active images when all content levels were enabled. The unchanged v12
source remains as the promotion backup.

## Content level curation – historical dataset count

Prompt-catalog repair uses the separate `content-levels audit/recover`
workflow. Its versioned curation enumerates all 803 active and archived stable
component UIDs and binds each decision to the latest revision UID and content
hash. The audit binds database and curation hashes and previews component,
generation and image transitions. Recovery copies the source into a new
database, updates canonical markers and generation snapshots, and removes
graph-inactive LoRA selections from the normalized relation in one short
transaction. Raw workflow provenance, source data and manual overrides remain
unchanged. The output is validated before promotion; backup and promotion stay
explicit operational steps.

## Historical image context completion snapshot

- Live canonical data completion is validated. ImageContext and scope queries
  can now use exact composition memberships for 363 generations; the sixteen
  unresolved cases remain explicit diagnostics rather than guessed relations.
  Application ImageContext will remain free of HTTP URLs; a response mapper
  combines it with `OutputFileUrlMapper` at the presentation boundary.
