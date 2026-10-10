# ComfyReview – Repository Engineering Rules

**Dokumentklasse:** `ENGINEERING_RULES` – für geänderten ComfyReview-Code, keine feste Character-Chronicles-Architektur.

Status: binding engineering baseline as of 2026-09-28.

These rules apply to all new and changed code immediately. Existing code that
violates them is technical debt to be migrated deliberately; do not copy or
extend an existing violation merely because it already exists.

## Python and architecture

- Python follows PEP 8 and uses explicit, descriptive English names.
- Use OOP at stateful boundaries. Repositories, providers, long-lived workers,
  stateful services and resource owners are classes.
- Pure calculations and small stateless transformations may remain functions.
- Every function or method performs one coherent task. Orchestration belongs in
  higher-level services; implementation details belong in focused lower-level
  collaborators.
- Dependencies are injected explicitly. Business services do not import
  concrete database paths, HTTP clients or filesystem locations from global
  configuration.
- HTTP/UI boundaries translate requests and responses. They do not contain
  persistence logic or business rules.
- SQL exists only in repository implementations and explicit offline migration
  or audit adapters. Services, routes, providers and domain objects do not
  execute SQL.
- External calls to ComfyUI or other APIs exist only in providers. They are
  bounded by timeouts, surfaced as explicit typed failures and logged with
  trace context.
- Filesystem access that represents an external system boundary (ComfyUI output
  discovery, sidecar loading, moves, exports) belongs behind a provider or
  dedicated adapter rather than being spread through routes and services.
- Domain objects know neither SQLite, FastAPI, HTTP, filesystem paths as
  persistence contracts, nor JSON serialization details.
- JSON is translated at technical boundaries. Internally prefer typed domain
  objects and explicit value objects.
- Stateful resources have an explicit lifecycle and a single owner.
- Do not hold a SQLite write transaction open while waiting on ComfyUI, the
  filesystem, or another external dependency.
- Mutations that belong together are atomic.

## Persistence and data model

- The target runtime has one canonical writable ComfyReview SQLite database.
- Legacy SQLite files are migration sources or rebuildable projections; they do
  not define the future runtime architecture.
- Stable IDs are canonical identity. File paths are attributes, not identity.
- Raw ComfyUI metadata may be retained for provenance, but application logic
  uses normalized fields and typed domain concepts.
- Derived data must be identifiable as derived and rebuildable from canonical
  facts. Do not duplicate large prompt, image or rating payloads per event when
  a normalized relation can preserve the same information.
- Do not eagerly materialize the full Cartesian product of all possible prompt
  combinations. Authored catalog entries, drafts and immutable prompt
  revisions are domain-relevant even before their first generation and must be
  retained. A composition is persisted when it is explicitly authored,
  generated, curated or otherwise selected as domain data.
- Schema changes are explicit and versioned. Runtime startup must not silently
  mutate an unknown or unsupported database into a new schema.
- Existing databases are never destructively migrated without a backup and an
  explicit migration command.

## ComfyUI integration

- ComfyUI is an external provider, not part of the domain layer.
- Workflow blueprint loading belongs behind an injected repository or source.
- Semantic workflow compilation belongs to a dedicated `WorkflowCompiler`.
  The compiler maps explicit roles to graph inputs and outputs; it does not
  perform HTTP calls or decide output naming policy.
- The ComfyUI provider owns workflow submission, external job status/history,
  capability discovery and retrieval of raw output descriptors. It accepts
  already compiled graphs and does not interpret semantic prompt/sampler roles.
- The application-owned `GenerationOutputCollector` combines those raw
  descriptors with the injected filesystem output source, canonical SQLite
  output repository and optional image-geometry projection. File validation,
  output identity and canonical persistence do not belong inside the ComfyUI
  API provider.
- Long-running ComfyUI jobs are modeled as asynchronous work. A client timeout
  is not equivalent to a failed generation.
- Generated image identity and generation metadata must remain reproducible
  even if output files are moved later.
- Native ComfyUI generation uses the provider API for prompt status/history
  and output descriptors. The existing output collection and persistence
  boundaries normalize generation metadata and provenance. New canonical
  generations must not depend on a repository-specific metadata export custom
  node or an accompanying JSON sidecar.
- Historical custom-node JSON sidecars are legacy import evidence only, handled
  by explicit audited `legacy-output` import adapters. Preserve available raw
  metadata as provenance, but do not reintroduce sidecars or custom-node export
  as requirements for the native generation runtime.

## Tests and quality

- No new stable concrete public Python-Core behavior boundary is accepted
  without an explicit behavior test.
- Maintain a function-to-test manifest for stable public Python-Core behavior
  boundaries. Constructors, private delegation methods, trivial accessors and
  dunder methods are tested through public behavior rather than registered as
  separate contracts. Complex private domain logic must be extracted into a
  testable policy/value boundary or be fully exercised through the public API.
- Target 100% statement coverage for the Python core. Any exception must be
  narrow, documented and explicitly approved.
- Test success paths, failure paths and transactional rollback where relevant.
- Provider tests use fakes/mocks and deterministic fixtures by default; real
  ComfyUI smoke tests are separate integration tests.
- Architecture tests enforce dependency boundaries, especially:
  - routes do not import SQLite
  - services do not execute SQL
  - repositories do not call ComfyUI
  - domain does not import FastAPI/SQLite/providers
- Passing linters and tests does not replace responsibility review.
- Before each intermediate commit, run focused behavior tests plus formatting,
  linting and typing for every changed file. This targeted mode is feedback,
  not integration evidence.
- The complete shared quality gate must run formatting, linting, typing,
  automated Python/frontend/browser tests, coverage and architecture checks
  at the end of every refactor slice and before integration.
- **The project owner performs the final manual tests and acceptance.**
  Developer/CI checks and tool-based review are necessary preparation, not
  proof of final real UI, provider or private-database acceptance. Record
  final user test outcomes only when supplied or explicitly confirmed by
  the project owner; do not assert them from a green CI run.

## Logging and tracing

- Use structured logging for externally visible workflows.
- Propagate a trace/correlation ID across HTTP request -> service -> provider or
  background job where applicable.
- Log meaningful state transitions and failures; do not log full private prompts,
  credentials, cookies, tokens or unnecessary image metadata.
- Errors at technical boundaries are normalized before reaching higher layers.

## Frontend and templates

- Jinja templates render markup and bootstrap values. They do not own business
  rules, persistence or complex request orchestration.
- New browser logic uses native ES modules.
- Browser functions/variables use `camelCase`, classes use `PascalCase`, module
  filenames use `kebab-case`.
- Requests go through one shared frontend API module. Views/components do not
  call `fetch()` directly.
- Render dynamic untrusted values as text or attributes. Do not introduce new
  dynamic `innerHTML` construction.
- Stateful browser components own and dispose listeners, timers and in-flight
  requests.
- No TypeScript migration is required for this refactor. Public JS module
  boundaries receive JSDoc contracts and `checkJs` validation.

## Documentation

ComfyReview is the **current, actively developed codebase** on a long-term
path toward Character Chronicles. This evolution uses POCs; **do not**
turn imported concepts, old M6/schema claims or discarded architecture into
binding rules merely because a historical document says “approved”.

For product-documentation changes, retain the **approximate** current
priority as **Card Battler → Timeline → Social Network with character
chat → Storyline → VN content last**. Timeline may be the first bounded
social slice. The **confirmed final world vision** is Japan/Kobe from 2032,
grounded anime near future, two postsecondary adult Academy years, a
culturally established social/card-battler platform, a protagonist moving
into Kobe and independent characters with personal histories, knowledge
and relationships. The Academy is **not an optional story premise** but
also **not a separate mandatory implementation phase**. The eventual
VN/dating-sim story is the long-term narrative center even though its
content is built last. Future implementation detail, phase boundaries
and technical choices remain open until explicitly reviewed.
Do not translate this orientation into a rigid schedule, POC ban or a
revived historical Chronicle MVP. Source of truth:
`docs/PROJECT_EVOLUTION.md`, `docs/character-chronicles/vision/world.md`
and `docs/character-chronicles/vision/README.md`. Keep the confirmed
story-world intent distinct from historical M6/schema/phase contracts.
Proofs of concept may refine the path and individual details but do
not silently revoke this confirmed world target.

Historical `docs/character-chronicles/sources/` content must keep its
original wording **and original relative links**. Do not retarget legacy
Foundation/M4/M6 references to present-day `vision/` or `README.md` pages.
Explain unavailable old targets in the source index or a separate provenance
note instead; report historical missing links distinctly from broken current
documentation navigation.
Run `python scripts/check_documentation.py` and
`python -m pytest tests/test_documentation_links.py` after editing current
navigation or historical source boundaries. These tests deliberately skip
**old source bodies**, not their current explanatory headers.

The [documentation map](docs/README.md) assigns a single current owner
for each category: general status, active POCs, refactor acceptance, open
decisions, operations, working vision and historical evidence. Keep those
boundaries consistent rather than duplicating live status in historical text.

When ComfyReview behavior or architecture changes, update the relevant
documents **for the current code**:

- `README.md` for user-facing setup and current behavior
- `docs/ARCHITECTURE.md` for the current runtime
- `docs/DATA_ARCHITECTURE.md` for present persistence/migration semantics
- `docs/CODING_STANDARDS.md` for current engineering baseline
- `docs/REFACTOR_PLAN.md` for current refactor scope and pending acceptance;
  its older slice history belongs to `docs/archive/refactor-slice-history-2026-10-09.md`
- `docs/project_status.md`, `docs/IMPLEMENTATION_AUDIT.md` for
  implementation claims, with exact commit/CI evidence
- `docs/ACTIVE_WORK.md` and `docs/pocs/` for in-progress experiments
- `docs/OPEN_DECISIONS.md` for genuinely unresolved decisions
- `docs/CONFIRMED_CONSTRAINTS.md` for confirmed scoped project constraints,
  clearly separated from preferences and technical candidates

The code baseline **before** the 2026-10-09 documentation import is
`a5f4131`; `76d71f9` only added/moved documentation. Do not mistake
the imported Chronicle concepts for code in that baseline.
[Project Evolution](docs/PROJECT_EVOLUTION.md) and
[Decision Policy](docs/DECISION_POLICY.md) define how old concepts are
reviewed: a past, discarded Chronicle implementation or an old Card Battler
plan may provide useful ideas, but does **not** fix the new architecture.

The shared monthly budget for **all billable external AI API calls** in this
ComfyReview-to-Character-Chronicles project is **below EUR 10**, including
paid development experiments, tests and later application requests.
Read [confirmed scoped constraints](docs/CONFIRMED_CONSTRAINTS.md) before
adding billable AI interactions; the proposed ~EUR 8 app cutoff is **not**
a verified existing control or a finalized technical design.

The Card Battler is **active POC work** in ComfyReview; isolated deterministic
tests do not prove an integrated playable game. The Generator was recently
reworked and catalogue/database optimization and real operator cutover remain
open; do not call those complete solely because schema/migration code exists.

Do not claim migration, private data metrics, hardware smoke or quality gates
passed without concrete evidence. Keep the eventual Character Chronicles
architecture revisable rather than inheriting all present ComfyReview
design constraints as permanent.

## Git and change discipline

- Work on a named feature/fix/refactor/docs/test branch per task.
- Do not commit runtime databases, generated image output, secrets, local paths,
  backups or model files.
- Review staged diffs before commit.
- Refactors preserve behavior unless the task explicitly changes behavior.
- Data migrations produce a new output database first; do not overwrite the
  source database in place.
- Do not claim migration, quality, coverage or architecture gates have passed
  unless the corresponding command was actually run successfully.
