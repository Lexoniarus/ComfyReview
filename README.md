<div align="center">

# ComfyReview

**Local review, curation, and analysis for ComfyUI outputs**  
Built for character-focused image workflows, especially anime-style generation and later LoRA-oriented curation.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-local_app-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)
![ComfyUI](https://img.shields.io/badge/ComfyUI-metadata_workflow-6A5ACD)
![Status](https://img.shields.io/badge/status-public_prototype-informational)

</div>

> ComfyUI can generate a small mountain of images very quickly.  
> ComfyReview helps turn that pile into something you can actually review, compare, curate, analyze, and reuse.

ComfyReview is a local FastAPI and SQLite web app for reviewing AI-generated image batches from ComfyUI. It grew out of a practical workflow problem: once a character-focused ComfyUI setup starts producing large batches of variations, selecting the useful images becomes its own time-consuming process.

Instead of treating that step like endless file cleanup, ComfyReview turns it into a structured review flow: import audited outputs, rate images, compare candidates, filter by character and set, keep generation context attached, and prepare curated selections for later reuse or LoRA-oriented dataset building.

---

## Project status

ComfyReview is a public prototype and local workflow tool.

The current repository demonstrates a usable local review system with audited image import, rating, filtering, statistics, Arena comparison, Playground handoff, canonical SQLite persistence and native ComfyUI output collection.

It should not be treated as a polished packaged desktop application. The project is best understood as a practical tool and portfolio project that documents a real local AI workflow.

A functional Card Battler is an approved future product target after the
current refactor; it is not implemented or part of the current feature list.
Its manual card-development, deterministic rules, deck, local PvE and
battle-driven card-evolution boundaries are documented in the
[Card Battler target](docs/CARD_BATTLER_TARGET.md).

For a more detailed scope overview, see:

```text
docs/project_status.md
```

---

## At a glance

| What | Description |
|---|---|
| **Core purpose** | Review and curate ComfyUI generations locally |
| **Best fit** | Character-heavy workflows, especially anime-style image generation |
| **Main input** | Canonical generations and native ComfyUI outputs |
| **Required dependency** | A reachable ComfyUI API with the blueprint capabilities |
| **Main views** | Review, Top/Worst, Arena, Playground, Catalog, Generations, Analytics, Settings |
| **Storage** | One canonical writable SQLite database; legacy sources are offline migration evidence |
| **Main benefit** | Faster selection, cleaner curation, reproducible reuse |

---

## Why

ComfyUI is excellent at generating images fast. The trouble starts afterwards: lots of variations, lots of prompt tweaks, lots of near-duplicates, and suddenly the selection process becomes its own project.

ComfyReview exists to make that part easier:

- audit and import local PNG and JSON output pairs
- review images with direct 1 to 10 ratings and delete actions
- compare candidates in Arena-style A/B views
- filter results by character and set
- keep prompt and generation context attached to each image
- send selected values back into the Playground Generator
- build curated image collections for character-focused LoRA workflows

---

## What it does

- Review generated images in a local web UI
- Rate images on a 1 to 10 scale
- Compare images in pairwise Arena views
- Filter by character and set
- Track prompts, sampler settings, checkpoint, seed, steps, cfg, scheduler and denoise values
- Analyze local results with shared observed/predicted render guidance
- Reuse selected generation values in the Playground Generator
- Maintain persistent UI state for generator inputs
- Load heavier generator-side data lazily to keep the page responsive
- Read Top and Arena from canonical image and review facts

---

## ComfyUI integration

New Playground generations use Blueprint v4 and the fixed
`VAEDecode -> 4x-AnimeSharp -> ImageSharpen -> Lanczos -> SaveImage` path.
The browser selects one of five format/orientation values and an HD, Full-HD
or maximum-quality output class. The highest class preserves the complete 4x
AnimeSharp dimensions for every format (from 4096 x 4096 square up to 5120 x
2880 widescreen); the server resolves both latent and exact target dimensions.
No repository-specific ComfyUI custom node is required at runtime.

Matching JSON sidecars remain supported as historical import evidence. They
are not required for newly generated canonical images or for already-canonical
images whose sidecars are absent.

Ambiguous native submissions are never retried automatically. Reconcile a
known generation against its persisted outputs and ComfyUI history with:

```powershell
python -m comfyreview generation reconcile GENERATION_UID
```

If a timed-out submit was accepted but its prompt ID was not returned, identify
that prompt in ComfyUI and attach it explicitly with `--prompt-id PROMPT_ID`.

---

## Main views

| View | Purpose |
|---|---|
| **Review** | Fast rating and delete workflow for image batches |
| **Top** | Aggregated best-image views |
| **Arena** | Pairwise comparison flow |
| **Analytics** | Coverage, canonical Scopes, prompt combinations and four-mode render guidance |
| **Playground** | Top-combination overview plus explicit generator workflow |
| **Catalog** | Prompt components plus the separate revisioned LoRA catalog |
| **Generations** | Lifecycle, reconciliation, provenance and all outputs |
| **Settings** | Workspace preferences, content levels, LoRA status, ComfyUI/upscaler status and diagnostics |

---

## Quick start

### Requirements

- Python 3.11+
- historical PNG/JSON pairs only when importing legacy output
- a running ComfyUI instance for Playground Generator features
- ComfyUI's standard upscale/sharpen/scale nodes and
  `models/upscale_models/example-upscaler.pth` for Blueprint v4 generation

### Installation

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

For development and repository quality checks, install the pinned toolchain:

```bash
pip install -r requirements-dev.txt
```

### Configuration

ComfyReview is configured through `config.py`, optional environment variables, and
an optional local `.env` file (copy `.env.example` to `.env`). Explicit environment
variables take precedence over values from `.env`.

The default paths are development-oriented and safe for a fresh clone, but they should be adjusted for your local ComfyUI setup before serious use.

Important settings:

| Setting | Environment variable | Purpose |
|---|---|---|
| `OUTPUT_ROOT` | `COMFYREVIEW_OUTPUT_ROOT` | Root boundary for canonical files and audited output imports |
| `COMFYUI_BASE_URL` | `COMFYREVIEW_COMFYUI_BASE_URL` | Local ComfyUI API URL |
| `WORKFLOWS_DIR` | `COMFYREVIEW_WORKFLOWS_DIR` | Folder for workflow files |
| `DATA_DIR` | `COMFYREVIEW_DATA_DIR` | Local runtime data folder |
| `SSL_ENABLED` | `COMFYREVIEW_SSL_ENABLED` | Enables local HTTPS when configured |

Example on Windows PowerShell:

```powershell
$env:COMFYREVIEW_OUTPUT_ROOT="D:\ComfyUI\output"
$env:COMFYREVIEW_COMFYUI_BASE_URL="http://127.0.0.1:8188"
python main.py
```

### Run

```bash
python main.py
```

Then open the local app in your browser. By default, the app runs on:

```text
http://127.0.0.1:8000
```

At startup, ComfyReview prepares its runtime directories and validates or
initializes only the canonical `comfyreview.sqlite3` database. Legacy SQLite
files are not runtime dependencies and no projection worker is started.

Review, Top/Worst, Arena, Curation, the Prompt Catalog, analytics and native
Generation use the canonical database. Images are addressed by stable UIDs;
their current PNG and optional sidecar paths are mutable attributes.

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
source database changed since audit. It creates and fully validates a new
database, removes historically deleted images, preserves Character identities
and revisions, migrates safe atom/render evidence, and only then resets image
reviews, Arena and Curation. Add `--replace` only while the application is
stopped to atomically install the validated output. This explicit workflow
does not create an additional backup.

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

## Basic workflow

1. Point ComfyReview at the correct ComfyUI output folder and API endpoint.
2. Upgrade the canonical database explicitly when the schema command requests it.
3. Audit and import historical PNG/JSON pairs with the maintenance commands.
4. Start ComfyReview locally and open the web UI.
5. Review images with ratings, deletes, filters and Arena comparisons.
6. Use Top, Stats and Playground pages to generate, reuse and analyze results.
7. Build curated character and set selections for later dataset or LoRA-oriented work.

---

## Character and set semantics

ComfyReview uses two separate filter axes:

- Character
- Set

That means views such as **Character = All** and **Set = Face** are meant to work across multiple characters at once.

This matters for character-focused curation workflows, where different images may belong to the same logical set category while still belonging to different characters.

---

## Local-first design

ComfyReview is designed as a local tool.

- Canonical images are discovered from the canonical database and read from
  local files
- Reviews, Arena matches and Curation assignments use one canonical SQLite
  database
- Legacy databases are explicit historical audit/import or maintenance inputs,
  never runtime authorities
- Runtime state and generated databases are intentionally ignored by Git
- ComfyUI integration expects a local or user-controlled ComfyUI instance
- No cloud service is required for the core review workflow

The repository is not intended to contain private image outputs, model files, personal ComfyUI paths, certificates, keys or runtime databases.

---

## Project structure

```text
ComfyReview/
├── comfyreview/              # settings, bootstrap, lifecycle ports/adapters
├── app.py
├── main.py
├── config.py
├── routers/                  # page routes and API endpoints
├── services/                 # HTTP/view composition awaiting final audit
├── quality/                  # versioned quality and architecture baselines
├── scripts/                  # shared repository automation
├── templates/                # HTML templates
├── static/                   # CSS, JS, assets
├── data/                     # local runtime data, ignored where needed
├── tests/                    # test suite
└── README.md
```

---

## Architecture notes

<details>
<summary><strong>Canonical image catalog</strong></summary>

The image catalog reads canonical image identities and mutable file attributes
from SQLite through a real read-only connection. Historical output discovery
and sidecar parsing happen only in the explicit audited import workflow.

</details>

<details>
<summary><strong>Review flow</strong></summary>

The review side of the app is built to make large batches of similar images easier to work through without turning the whole thing into manual sorting work.

Ratings, deletes and restores append canonical `review_events`. The UI still
shows the current effective state, derived from that history. Compatibility
views expose old query shapes but cannot be written.

</details>

<details>
<summary><strong>Generator reuse</strong></summary>

The Playground Generator is designed to carry values back into ComfyUI in a reproducible way instead of relying on memory and manual copy-paste.

`/playground` is the evidence overview for combinations with two or three
additional factors beside the always-present character;
`/playground/generator` is an experiment workspace with the explicit flow
`Setup konfigurieren -> Varianten vorbereiten -> vergleichen/bearbeiten ->
Auswahl generieren`. Fixed catalog groups show their positive and negative
atoms in Setup and keep edits local to the experiment. “Als Katalog-Test
speichern” is the only action that materializes such edits as a manual prompt
candidate; Reset restores the exact bound catalog revision. Random groups have
no editable atoms until the server resolves them into concrete variants.

The sampler always shows its concrete Steps, CFG and image seed. Optional
Steps/CFG/seed ranges live behind “Variieren”; variant count defaults to four
and is bounded to 1-12. The server returns preferably diverse transient drafts
with unique/repeated counts and an exhaustion notice. Each card has its own
draft UID, resolved prompt groups and concrete sampler values. Setup changes
keep the old cards visible but mark them stale and block submission until they
are refreshed. Every selected reviewed card submits exactly one generation
through the batch boundary; partial failures stay associated with their draft
UID. Preparing variants does not persist drafts and adds no database schema.
On wide desktops, cards and Inspector remain visible together. Laptop widths
open the Inspector as a dismissible drawer; tablet widths use explicit Karten
and Inspector tabs. All three layouts keep the generation action in the normal
document flow, remain keyboard-operable and honor reduced-motion preferences.

Each fixed prompt group keeps its concrete source revision and may also keep a
concrete candidate. Its variant control independently offers the
promoted stable/provisional catalog recipe, the most recently authored manual
catalog variant, the stable recipe's calculated weight-only optimum and the
stable recipe's next useful weight test. The manual variant remains available
after generation, review or promotion. Calculated guidance is materialized
only after the user selects it; applying any variant replaces only that
group's atoms in the ordinary editable `PromptAtomEditor`.
Variant and generation payloads retain the exact group, source revision,
candidate and rendered atom usages. The compatibility single-draft and sweep
HTTP contracts remain available for older callers, but the workspace uses
`POST /api/v2/playground/variant-batches` and
`POST /api/v2/generations/batch`.

`POST /api/v2/playground/prompt-guidance` binds to an expected current catalog
revision and returns its recipe, best observed recipe, calculated optimum,
discovery test, support, uncertainty, example images and coverage. The server
rejects a stale source revision instead of calculating from manually loaded
atoms. Explicitly selected calculated recipes are deduplicated by
`POST /api/v2/playground/prompt-candidates`. The catalog API exposes both the
promotion-selected `current_revision` and the numerically highest historical
`latest_revision`.

The Render/Sampler controls offer four explicit evidence modes: observed or
predicted, each for a complete setup or individual values. Applying one changes
only Checkpoint, Sampler, Scheduler, Steps, CFG and Denoise; LoRAs and output
geometry remain manual. Generation history is available at `/generations`.

The application lifespan owns one generation observer, so submitted Playground
jobs continue from `submitted` through output collection and `completed`
without a browser-owned queue. Transport interruptions are retried; ambiguous
submissions are never automatically sent twice. If ComfyUI history has expired,
the explicit reconcile action can accept only an exact, unambiguous output from
the generation's persisted directory and filename prefix.

Analytics uses the same `render-guidance-v1` calculation. Every Review,
Top/Worst, Arena, Analytics, Catalog, Generations and Playground evidence
action navigates directly through the shared Generator handoff codec.
Prompt/LoRA handoffs replace the visible “01 Auswahl” state with fully
catalog-bound, normally editable component and ordered LoRA controls, while
render-only handoffs leave it untouched. There is no tray, toast event or
hidden prompt editor, and no draft exists until “Varianten vorbereiten” is
pressed. Exact image handoffs may restore archived historical component
revisions; those entries are labelled `Archiv`, remain manually editable and
are never candidates for random selection. Image cards and inspectors expose
normalized trigger-evidenced LoRAs alongside component scopes. Successful
handoffs clean their URL parameters; rejected handoffs
keep the prior state and display the error in the Generator. LoRA revision
triggers enter the matching positive or negative prompt exactly once. Removing
every trigger of a selected LoRA blocks preview and submission before
persistence.

Successful Review, Delete and Arena writes trigger best-effort prompt promotion
reconciliation in a separate short transaction. A reconciliation failure never
rolls back the stored feedback: the response marks `promotion_pending`, and
`python -m comfyreview prompt-promotions audit|reconcile --database <path>`
provides the explicit idempotent recovery path. Startup performs no silent
schema upgrade or promotion.

</details>

<details>
<summary><strong>Canonical and legacy projections</strong></summary>

Top/Worst, Arena and analytics use canonical review facts and image UIDs. The
legacy projection worker is no longer part of runtime startup; legacy database
files are accepted only by explicit offline maintenance commands.

Review places newly captured unrated images first and then returns to the image
with the oldest rating sequence. Arena derives its cooldown from canonical
match history: unchanged reloads keep the current pair, while a saved decision
rotates both images behind older eligible candidates before offering a reverse
direction.

</details>

---

## Testing

Run the test suite with:

```bash
python -m pytest
```

Before review or integration, run the complete shared quality gate:

```bash
python scripts/quality.py
```

The gate runs Ruff, formatting, mypy, Pyright, all tests, architecture checks,
the function-test manifest and 100% statement coverage for the defined Python
core. Existing pre-baseline violations remain visible in versioned ratchet
files; new and changed Python files must pass without adding exceptions.

The repository may include sample PNG and JSON files that can be used as
audited import input for local testing.

---

## Known limitations

- This is a local prototype, not a packaged desktop application
- Configuration still requires direct path and environment setup
- Historical output import depends on retained sidecar metadata; native
  generation uses standard ComfyUI nodes and canonical output collection
- New historical output imports require a JSON sidecar; already-canonical
  sidecarless images remain usable in Review, Top/Worst, Arena, Curation and
  Delete
- Export and dataset-building workflows are not final production pipelines
- Frontend V2 uses Jinja shells and native ES modules; Playground previews and
  submission use immutable canonical prompt revisions and the native
  GenerationService
- Public documentation may lag behind internal workflow experiments

---

## Not the goal of this version

- Fully redesigned data identity model
- Full separation of curation truth from physical folder layout
- Final export or packaging architecture for future LoRA dataset builds
- Multi-user hosting
- Cloud deployment
- Public SaaS operation

---

## Contributing

This is primarily a personal local workflow tool, but the public repository documents the approach and implementation.

If you change behavior in this project, avoid silently breaking the workflow assumptions that make the app useful in practice:

- required PNG and JSON pairing
- character/set filtering semantics
- generator state persistence
- lazy loading behavior in generator-related views
- reproducible value handoff back into ComfyUI
- local-first runtime data separation

---

## License

The project code is licensed under the MIT License. See `LICENSE`.
