# ComfyReview – Datenbank-, Import- und Wartungsbefehle

**Dokumentklasse:** `CURRENT_OPERATIONS_GUIDE` · **Quellenstand:** `refactor/review-boundary` / Anwendungscode `a5f4131` (2026-10-08).  
**Geltungsbereich:** **gegenwärtige ComfyReview-CLI**; kein neuer Character-Chronicles-Architektur-/Migrationsplan.

> **Sicherheit:** Schema-v18-Unterstützung im Code ist **keine Bestätigung**, dass die reale private Datenbank bereits v18 verwendet oder redaktionell normalisiert ist. Rehearsal, Quellhash, validierte Ausgabe, echte Backups, Anwendung im gestoppten Zustand und ausdrückliche Operatorentscheidung sind entscheidend. Vor einem `--replace` den eigenen Datenbestand, den aktuellen CLI-Vertrag, Dateipfade und Sicherungen überprüfen. Die folgenden Beispiele stammen aus der bisherigen Repository-README; ihre realen Pfade sind **Beispiele**, nicht bereits vorhandene private Dateien.

## Canonical SQLite und importierte Bestandsdaten

### Canonical database and audited imports

Validate or explicitly upgrade the canonical database:

```bash
python -m comfyreview canonical-db validate
python -m comfyreview canonical-db upgrade \
  --output data/comfyreview-v18.sqlite3 \
  --backup-dir data/backups/canonical \
  --generator-state data/ui_state/playground_generator_last.json
python -m comfyreview canonical-db rebuild-image-geometry
```

Normalize an existing Playground catalog through a source-hash-bound audit and
a private editorial mapping:

```bash
python -m comfyreview catalog-normalization audit
python -m comfyreview catalog-normalization rebuild \
  --output data/rehearsals/comfyreview-normalized.sqlite3
```

The audit writes its report below `data/reports/` and its editable mapping
below ignored `data/rehearsals/`. Rebuild refuses an incomplete mapping or a
mapping whose own checksum or source binding changed since audit. Every
Non-Character source must be explicitly replaced or dropped: `keep` is not a
valid cleanup decision. Replacement components always receive a new UID and
start at revision 1, while Character—including promotions and manual
variants—is preserved exactly. Rebuild creates and fully validates a new
database, removes historically deleted images, migrates safe atom/render
evidence, binds every retained generation to quality and content policies, and
only then resets image reviews, Arena and Curation. Add `--replace` only while
the application is stopped to atomically install the validated output. This
explicit workflow does not create an additional backup.

Before replacement, run the rebuilt rehearsal database through the normal
application entry point on a separate local port:

```powershell
$rehearsal = (Resolve-Path `
  "data\rehearsals\comfyreview-normalized.sqlite3").Path
$env:COMFYREVIEW_DATABASE=$rehearsal
$env:COMFYREVIEW_PORT="8016"
python main.py
```

Open `http://127.0.0.1:8016`. Settings must show the exact rehearsal database
path and schema v18. Review, Top/Worst, Arena, Playground Catalog, Generator,
Handoff, Scopes and Analytics are the ordinary runtime surfaces; there is no
separate test catalog or test mode. Confirm the eleven prompt groups, the
absence of `modifier`, an unrated Review queue, empty Top/Worst and Arena, and
an editable handoff for retained images. Old Non-Character revisions required
by immutable generation provenance remain technical-only; authored
compositions containing them deliberately resolve to no selectable handoff.

Manual ratings or other writes make this rehearsal file disposable. Stop
`main.py`, clear the temporary environment variables, and never install the
tested file. After explicit acceptance, rebuild once more from the unchanged
source and reviewed mapping while the canonical application is stopped:

```powershell
Remove-Item Env:COMFYREVIEW_DATABASE
Remove-Item Env:COMFYREVIEW_PORT
python -m comfyreview catalog-normalization rebuild `
  --output data/rehearsals/comfyreview-normalized-cutover.sqlite3 `
  --replace
python main.py
```

If the source hash changed after audit, rebuild stops and requires a new audit
and editorial review. The final `--replace` command is intentionally withheld
until the rehearsal has been accepted explicitly.

The v11 geometry rebuild reads PNG headers outside a write transaction and
then atomically replaces the rebuildable projection. Missing or malformed
files are reported as diagnostics; source images and stored paths are never
rewritten.

Historical ComfyUI output provenance is imported through a read-only audit
followed by a separate write command:

```bash
python -m comfyreview legacy-output audit
python -m comfyreview legacy-output import --backup-dir data/backups/legacy-output
```

Legacy Review, Arena and Curation facts use the same two-step contract:

```bash
python -m comfyreview legacy-features audit
python -m comfyreview legacy-features import --backup-dir data/backups/legacy-features
```

The legacy Playground catalog and provably exact historical composition links
are completed separately:

```bash
python -m comfyreview legacy-prompts audit
python -m comfyreview legacy-prompts import --backup-dir data/backups/legacy-prompts
python -m comfyreview legacy-compositions audit
python -m comfyreview legacy-compositions import --backup-dir data/backups/legacy-compositions
```

Composition completion links only a unique ordered set of immutable revisions
identified as complete prompt-atom blocks. Additional historical draft text
remains in the unchanged generation snapshot; it is not invented as a new
catalog revision. Ambiguous or incomplete evidence remains unlinked and is
reported rather than guessed.

For retained generations that contain richer embedded recipes or have been
manually reviewed against their exact prompt snapshots, provenance recovery is
an explicit new-database operation:

```bash
python -m comfyreview legacy-provenance audit \
  --curation migrations/legacy-provenance-curation-v2.json
python -m comfyreview legacy-provenance recover \
  --output data/rehearsals/comfyreview-legacy-provenance-v2.sqlite3
```

The audit distinguishes embedded recipe evidence, exact catalog matches and
curated prompt reconstruction. Recovery refuses to overwrite its source,
requires zero unattributed prompt atoms and zero ambiguous LoRA bindings,
validates the completed output database and leaves existing current catalog
revisions unchanged as the latest revisions. Recognizable historical variants
become prior revisions of their real component; no generic remainder component
is created.

The active application schema is v18. Prompt Catalog revisions and Playground
drafts expose ordered positive/negative atom rows with separate numeric
weights. Rendered whole prompts remain exact provenance snapshots produced by
the server; they
are not a second editable source of truth. Schema v8 stores typed workspace
preferences, generation profiles and ordered LoRA stacks. Schema v9 adds
ordered workspace content levels plus explicit generation canvas dimensions.
Schema v10 adds resolved target geometry, stable LoRA catalog
identities and generation snapshots, inferred generation content levels, and
append-only image-classification events with a rebuildable current override.
Schema v11 adds the rebuildable `image_geometry_projection`; the explicit
rebuild command reads actual PNG header dimensions outside a transaction and
atomically replaces the projection. Schema v12 turns stable LoRA definitions
into a first-class catalog with immutable default/trigger revisions and stores
the selected LoRA revision on new generation usage; historical usages remain
nullable rather than being assigned invented current triggers. Schema v13
stores the Generator's render/seed singleton, prompt-role selections and
ordered revision-pinned LoRAs in the same canonical database. The optional
`--generator-state` input imports a validated legacy `generator_v2` snapshot
only during the explicit copy migration. Schema v14 moves LoRA content
classification onto the immutable trigger revision. Normalized LoRA usage is
retained only when its loader is graph-effective and at least one exact
revision trigger occurs in the matching final prompt scope. Triggerless raw
loader nodes remain technical provenance but cannot raise an image's content
level. Standard content visibility is
enforced by canonical repository queries across
Top/Worst, Review, Arena, Scopes, Analytics, Catalog evidence and Playground;
the browser does not reimplement that policy. Existing older databases require
the explicit backed-up `canonical-db upgrade` command before startup.
Settings may enable any non-empty subset of the five levels, including a view
that excludes `Standard`; at least one level must remain enabled.

Schema v15 adds deduplicated prompt candidates, exact per-generation prompt
groups and append-only catalog promotions. Schema v16 adds the separate
append-only manual-variant selection history. The current catalog standard is
the newest promotion, while `latest_revision` remains historical numbering and
`latest_manual_variant` remains available independently of generation, review
or promotion. Schema v17 adds current image catalog compositions, global prompt
policies and evidence baselines. Schema v18 marks superseded components as
generation-only provenance so they cannot re-enter the selectable catalog.

Generation profiles are no longer an active runtime or HTTP concept; their
tables remain dormant only for migration compatibility. The Generator owns
checkpoint, sampler, ranges, batch, classified LoRAs, format and output class
directly. Blueprint v4 executes `VAEDecode -> 4x-AnimeSharp -> ImageSharpen ->
Lanczos ImageScale -> SaveImage`; missing required nodes or the fixed upscale
model block submission before a generation is persisted. Settings lists LoRA
status and links to the single editor in Catalog. Detected LoRAs remain
separate from their canonical classification. A LoRA is selectable only when
its selected revision owns trigger atoms and a typed content level. Detected
or triggerless historical revisions are visible but cannot be submitted. Only
loader branches connected to a consumed sampler model or CLIP input with a
non-zero branch strength and evidenced by a scoped revision trigger become
normalized generation usage. Disconnected or triggerless historical nodes
remain raw provenance but do not affect content classification. Top/Worst includes every live image with at least one
rating, can override an image to any of the five content levels, return it to
automatic inference, or invoke the existing UID-based delete workflow.

Every image surface uses one shared handoff action. Prompt handoff and render
handoff are staged independently: the former carries authoritative prompt
snapshots, component provenance and graph-effective LoRAs; the latter carries
checkpoint, ordered sampler facts, seed and geometry. Unavailable provider
values remain visible and rejected instead of being silently substituted. In
Blueprint v4, the compiler validates every selected LoRA as an ordered,
continuous Model and CLIP loader chain before persistence or submission.

Prompt components expose a separate five-value content level in the catalog;
free tags are descriptive only. Existing installations can curate and repair
historical snapshots without a schema change:

```bash
python -m comfyreview content-levels audit \
  --curation migrations/prompt-content-level-curation-v1.json \
  --report data/reports/content-level-audit.json
python -m comfyreview content-levels recover \
  --report data/reports/content-level-audit.json \
  --output data/comfyreview-content-levels-v1.sqlite3
```

Recovery always creates and validates a new database; it also removes
graph-inactive historical LoRAs from the normalized usage relation while
preserving the original workflow JSON. Promotion and backup of the canonical
runtime database are explicit operational steps. Top/Worst,
Analytics and Playground card collections use three equal columns on iPad-sized
viewports, while every card keeps the full natural image ratio without crop.
Playground ranks combinations with two or three additional observed factors for
every canonical character. A shared diversity policy prefers a different
highest-rated cover image for every visible card across both groups and repeats
one only after the available unique evidence is exhausted. Each card still
retains its three strongest matching images. Analytics Overview, Scopes and
Render Analysis share the same cyclic three-card tablet language; horizontal
touch gestures and arrows wrap in both directions.

Audit reports bind source files and databases by hash. Import commands
revalidate that evidence, create a backup before writing, and commit all writes
in one canonical SQLite transaction. A normal transaction failure is rolled
back first; the backup is restored only when validation fails or the resulting
commit state is uncertain. Reports, backups and runtime databases are local
artifacts and are ignored by Git.

### Legacy database maintenance

Validate all configured legacy databases without changing them:

```bash
python -m comfyreview legacy-db validate
```

Validate only selected databases by repeating `--database`:

```bash
python -m comfyreview legacy-db validate --database ratings --database arena
```

Known additive legacy upgrades are explicit and backed up before mutation:

```bash
python -m comfyreview legacy-db upgrade --backup-dir data/backups
```

These commands load a separate offline `LegacyMigrationSettings`; the normal
application container has no legacy database paths. The command returns exit
code `0` on success, `2` for an invalid or unsupported
schema, and `1` for a technical failure. Upgrades restore affected files from
their backups when an ordinary upgrade or validation step fails. SQLite cannot
provide crash-atomic commits across several independent database files.
Cut-over Review, Arena and Curation writes avoid that limitation by using the
canonical database; remaining legacy projections retain it until migrated.

---


## Abgrenzung

Diese Befehle behandeln die aktuell implementierten ComfyReview-Daten-, Catalog- und Legacy-Grenzen. Die im [historischen Character-Chronicle-Code](character-chronicles/HISTORICAL_CODE_AUDIT.md) beschriebenen Schema-47-bis-58- und M6-Umstellungen gehören zu **einem verworfenen früheren Ansatz**; sie dürfen nicht auf die Canonical-v18-ComfyReview-Datenbank angewendet werden.

[Projektstatus](project_status.md) · [Datenarchitektur](DATA_ARCHITECTURE.md) · [Technischer Code-Audit](IMPLEMENTATION_AUDIT.md) · [Zurück zum Start](../README.md).
