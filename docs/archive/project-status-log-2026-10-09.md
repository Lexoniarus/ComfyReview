# Archiviertes Projektstatus-Protokoll (Stand der Dokumentation 2026-10-09)

**Dokumentklasse:** `HISTORICAL_LOG` · **Rolle:** früheres Status-/Operatorprotokoll – **KEIN AKTUELLER STATUS**.

Der folgende vollständige Text ist das **detaillierte frühere Status- und Betriebsprotokoll**. Darin vorkommende Wörter wie „live“, „current“, „latest“, „abgenommen“, historische Datenbankzeilen und lokale ComfyUI-Smokes gelten **jeweils nur für den berichteten damaligen Zustand**. Die realen Datenbanken, Backups und privaten Reports sind nicht Teil dieses Git-Repositories und wurden hier nicht neu vermessen.

**Gültiger Einstieg:** [Heutiger Status](../project_status.md), [laufende Arbeit](../ACTIVE_WORK.md), [Code-/CI-Nachweis](../IMPLEMENTATION_AUDIT.md). Für Fragen zur Zukunft: [Projektentwicklung](../PROJECT_EVOLUTION.md). Der Originaltext ist zur Nachvollziehbarkeit erhalten; seine Aussagen dürfen nicht unbemerkt zu aktuellen Release-Fakten werden.

---

## Überlieferte detaillierte Statusfassung

# Project Status

## Summary

ComfyReview is a local-first FastAPI workflow tool for reviewing, comparing,
curating, analysing and reproducibly regenerating ComfyUI outputs. The
integrated refactor base uses one canonical writable SQLite database and a
native ES-module Frontend V2.

## Implemented state

- canonical schema v18 with stable image/generation identity, rebuildable PNG
  geometry classification, immutable content-bearing LoRA trigger revisions,
  normalized Generator state and evidence-backed prompt variants;
- append-only Review events and rebuildable current-state/ranking views;
- UID-based Arena with history-derived fair rotation, and UID-based Curation;
- audited, idempotent historical Output, Prompt, Feature and Composition
  imports;
- audited legacy prompt-provenance recovery into a separately validated output
  database, with embedded, exact and reviewed evidence kept distinct;
- reviewed legacy prompt curation promoted on 2026-10-06: historical source
  revisions cover every old prompt block, including combined modifier/framing
  and lighting variants; these remain provenance inputs for the pending
  normalized-catalog editorial cutover; six active and
  two deleted malformed Hina snapshots were corrected through hash-bound
  offline recovery, so only attributable LoRA triggers remain outside normal
  prompt-component memberships;
- immutable prompt revisions, structured weighted atoms and reproducible
  compositions;
- eleven normalized Generator groups, versioned global prompt policies and one
  selected catalog composition per image; the hash-bound cleanup rebuild keeps
  Character exact, preserves safe atom/render priors, and resets image reviews,
  Arena and Curation only after complete validation;
- versioned workflow blueprints, dedicated compiler and technical ComfyUI
  provider;
- an application-owned generation lifecycle worker, explicit reconciliation,
  strict output recovery, multi-output collection and normalized sampler/LoRA
  provenance;
- canonical Analytics for Scopes, parameters, prompt combinations and observed
  render setups;
- Frontend V2 for Review, Top/Worst, Arena, Playground, Catalog, Generations,
  Analytics and Settings;
- workspace preferences, direct Generator settings, classified LoRA stacks,
  the fixed five-format/three-resolution matrix and cumulative content
  visibility; profile tables are dormant migration compatibility only;
- canonical stable-ID LoRA catalog with immutable trigger/default revisions,
  per-generation revision/classification snapshots, revision-checked
  historical reclassification and audited image overrides;
- shared Python/frontend quality gate with architecture tests, coverage and
  Playwright browser acceptance.

## Approved future product direction

A functional Card Battler prototype is approved as a post-refactor product
target. It is not implemented and is not part of current refactor acceptance.
ComfyReview will first prove the bounded Card Battler before Character
Chronicles may reuse it.

The target progresses from explicit manual image-to-card development and a
card collection through deterministic card functions, deck construction, a
server-authoritative local PvE game, anti-farm battle experience, revisioned
card evolution and its interactive board. Character Chronicles-specific
campaign, Champion, VN and social progression systems are excluded. The full
contract is documented in the
[Card Battler target](CARD_BATTLER_TARGET.md).

## Runtime rules

Normal runtime reads and writes only the canonical database. Legacy databases,
sidecars and path relationships are available solely to explicit offline
audit/import tools. Paths are attributes, not identity, and no cut-over feature
dual-writes legacy state.

New generation uses Blueprint v4 with the fixed 4x-AnimeSharp, sharpen and
Lanczos scale path. The model canvas and final target geometry remain separate.
HD and Full-HD are explicit smaller outputs; the maximum-quality class retains
the complete 4x AnimeSharp dimensions for all five formats, from 4096 x 4096
square through 5120 x 2880 widescreen. The compiler owns prompt, sampler,
output-role and LoRA graph semantics; the provider owns only transport, job
state, capabilities and raw output descriptors.

Generation is rejected before persistence or submission when required nodes or
`example-upscaler.pth` are unavailable. A selected LoRA requires an exact
content-bearing trigger revision. It counts only when its loader is
graph-effective and at least one revision trigger occurs in the matching final
prompt scope. New generation content level is the strictest of prompt-component
and evidenced LoRA-revision facts; a manual image override wins until it is
explicitly returned to automatic inference.

Blueprint v4 also rejects a selected LoRA unless its exact provider file,
revision and weights form one ordered loader chain from Checkpoint Model/CLIP
to the sampler and both text encoders. Prompt and render settings can be staged
independently from every visible image surface. The server, not the browser,
loads authoritative image snapshots and only graph-effective historical LoRAs.

One typed `PromptContentLevelPolicy` controls catalog classification. Every
component carries a canonical marker separate from descriptive tags; historical
visibility uses only its stored generation snapshot or a manual override across
Top/Worst, Review, Arena, Scopes, Analytics, Catalog evidence and Playground.
The browser does not filter an already-loaded superset, and no runtime
path/prompt heuristic acts as a second classification truth.

The complete 791-component content curation was audited and recovered on
2026-10-06 into a new validated schema-v11 database. It changed 44 component
classifications and 53 generation snapshots, preserved all manual overrides,
retained the previous runtime database as a backup and restarted the LAN
process. Standard-only Playground options no longer include Basic Underwear or
the other curated Sexy/Nude/Explicit components.

The same acceptance audit found 165 historical generations that used the
already-classified Explicit LoRA `example-lora-2.safetensors` before
LoRA snapshots were populated. Its revision-checked preview and atomic
reclassification were applied explicitly; manual overrides remained untouched.
Other legacy LoRAs with unclear historical semantics were not inferred or
bulk-reclassified.

The follow-up graph-effect audit found 208 historical `multiple-views` loader
entries whose outputs never reached the sampler or either consumed CLIP path.
The v2 content-level recovery was validated and promoted on 2026-10-06 with
the previous runtime database retained as a backup. It removed only those
entries from normalized `generation_loras`, preserved their raw
workflow/`loras_json` provenance and left all effective image-level totals
unchanged. Top/Worst no longer borrows the three-rating evidence threshold:
every live image with at least one rating is eligible when its content level
and other explicit filters are enabled.

New unrated images are prioritized in Review by newest canonical image ID;
after that queue is exhausted, rated images return by oldest review sequence.
Arena pairing derives a cooldown from immutable match order, so both candidates
rotate behind older eligible images before a reverse direction can appear.

The FastAPI lifespan owns the only automatic generation observer. It polls
submitted/running jobs every two seconds, completes canonical outputs through
the shared collector, retries transport failures and never resubmits ambiguous
work. Explicit reconcile may recover one exact persisted PNG when ComfyUI no
longer knows the prompt; ambiguous filesystem matches remain visible for human
attention.

The 2026-10-06 live LAN acceptance recovered all five previously submitted
jobs: one through retained ComfyUI history and four through explicit strict
filesystem reconciliation. All five now have one canonical output; no active
job remains submitted, running or reconciliation-required.

`/playground` now presents cyclic Top-2/Top-3 evidence per canonical character.
Analytics Overview, Scopes and Render Analysis use the same bounded three-card
tablet rail, with natural uncropped media and cyclic arrow/touch navigation.
The Generator uses one
server-materialized seed, server draft UIDs, grouped weighted atom overrides
and separate prompt/sampler evidence. Actual PNG geometry is visible in the
Inspector and available as a descriptive Analytics dimension.

Generator and Render Analytics share `render-guidance-v1`. The four modes
separate observed stability from modeled quality and complete setups from
individual values. Stability thresholds count independent images, while all
immutable rating/delete events contribute evidence weight. Checkpoint, Sampler,
Scheduler, Steps, CFG and Denoise participate; LoRAs, seed and geometry remain
manual. Guidance is derived on request and adds no schema or migration.

Prompt selections show visible catalog references, Draft and Analytics evidence
use large cyclic image carousels, and Steps/CFG use one accessible two-handle
track. Every source action navigates directly through one typed handoff owner.
Prompt/LoRA handoffs replace visible “01 Auswahl” controls, render handoffs
replace only render settings, and neither creates a draft. There is no
tab-local tray, global staging event or duplicate toast owner.
Exact image handoffs also restore archived historical component revisions into
the ordinary editable slots. They are labelled as archived and remain excluded
from random selection. Draft and generation contracts retain the ordered kind,
component UID and immutable revision UID through final confirmation; unchanged
historical slots are no longer rebound to current revisions. Top/Worst cards
and inspectors show normalized,
trigger-evidenced LoRA usages alongside component scopes. Content preferences
accept every non-empty subset of the five levels, including exclusion of
Standard, and the tablet scope rail is dismissible by its close action or an
outside tap.

Schema v12 was promoted to the live runtime database on 2026-10-06 through a
separately created and validated output database. The previous schema-v11
runtime database remains unchanged as a named backup. All 12 existing LoRA
definitions received one immutable basis revision; historical generation
usages retained nullable revision provenance where it could not be proved.

Schema v14 was promoted to the live runtime database on 2026-10-07 through the
explicit v12-to-v13-to-v14 copy path. The byte-identical v12 source remains in
the named promotion backup. The hash-bound provenance recovery audited 414
generations with zero unattributed atoms, zero over-attributed atoms and zero
ambiguous LoRA bindings. It retained 19 graph-effective, trigger-evidenced LoRA
usages with exact revision links and removed 832 unsupported normalized rows;
their raw graphs remain unchanged. All 393 active images produce a complete
editable Prompt handoff when their content levels are visible. The validated
runtime source audit contains 805 catalog components. The running source remains
schema v16 until the reviewed normalization output is explicitly installed.

Schema v16 was promoted on 2026-10-07 through a separately created and
validated output database. The v15 source remained unchanged until the
explicit replacement, the pre-promotion v15 database remains available as a
named backup, and both files passed `integrity_check`. The v15 source contained
no prompt candidates, so the v16 manual-variant backfill correctly created no
invented manual selections.

The live ComfyUI acceptance submitted and completed one generation with one
LoRA and one generation with two ordered LoRAs. Both produced exact 720×720
outputs through Blueprint v4. Their stored graphs, revision UIDs and strengths
confirmed the complete Checkpoint Model/CLIP -> ordered LoraLoader chain ->
KSampler and both CLIP encoders. The generation lifecycle worker collected
both outputs canonically.

## Acceptance and integration state

The catalog-normalization implementation slices are committed on
`fix/playground-combination-diversity`. The latest full shared quality gate is
green: 770 Python tests, 181 frontend tests and 14 Playwright acceptance tests
pass, with 100% Python-Core and frontend statement, function and line coverage.
The private editorial mapping and the explicit real-database `--replace`
cutover remain separate operator work. A dedicated behavior test now rebuilds
a fixture database and serves it through the real `python main.py` subprocess;
the real rehearsal uses the same entry point on a separate port. Manual
acceptance may write to that rehearsal, so it is never promoted: explicit
approval is followed by a fresh rebuild before `--replace`.
On 2026-10-05 the live v10 database was backed up, upgraded to v11 and
rebuilt without diagnostics: all 377 active images received geometry
projections. Real Blueprint-v4 ComfyUI smoke generations also completed for
2:3/720 (720×1080) and 3:2/720 (1080×720), and both captured PNG dimensions
matched their stored targets exactly.

The legacy-provenance rehearsal on the same schema-v11 source also succeeded:
385 generations were audited, 109 missing historical revisions were created in
the separate output database and 324 generations were relinked. The existing
latest revisions remained latest, all 377 active-image generations had a
character membership, and no ambiguous prompt slot remained.

The final Generator dead-path usage audit is complete; the obsolete browser
staging path, file-backed Generator state and unreferenced legacy Generator
services are removed. The former feature branches contain no unique commits
outside the refactor base. User-facing visual acceptance and the later decision
to integrate `refactor/review-boundary` into `master` remain open.

## Scope and limitations

ComfyReview remains a local tool rather than a hosted multi-user service or a
packaged desktop installer. Infrastructure paths and the ComfyUI endpoint are
still configured through the local environment. Historical imports need their
retained evidence; already-canonical sidecarless images remain usable. Export
and dataset-packaging workflows are not final production pipelines.

Project code is licensed under the MIT License. See `LICENSE`.
