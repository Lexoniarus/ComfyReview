# ComfyReview – Repository Engineering Rules

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
- Workflow submission, job polling, output collection and capability discovery
  belong to the ComfyUI provider boundary. The provider receives an already
  compiled graph and has no knowledge of prompt, sampler or output roles.
- Long-running ComfyUI jobs are modeled as asynchronous work. A client timeout
  is not equivalent to a failed generation.
- Generated image identity and generation metadata must remain reproducible
  even if output files are moved later.
- The repository-specific ComfyUI metadata export node remains a technical
  integration boundary; its payload must be mapped into canonical domain data.

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
- The complete shared quality gate must run formatting, linting, typing, tests,
  coverage and architecture checks at the end of every refactor slice and
  before integration.

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

Repository documentation authority and product scope are indexed in
`docs/README.md`:

- `docs/project_status.md` and code/tests describe the implemented state.
- `docs/ROADMAP.md` specifies the sequential evolution of the existing
  ComfyReview codebase toward Character Chronicles (Card Battler, Timeline,
  Social Network with chat, Storyline, and **VN content last**).
- `docs/DECISIONS.md` records explicitly adopted product decisions.
  `docs/POC_REGISTER.md` records experiments, never implicit approval.
- All files under `docs/archive/` (especially the abandoned
  Character Chronicles attempt) are **historical, non-normative evidence**,
  regardless of historical labels such as DECIDED, implemented, MVP,
  authoritative, or baseline complete. Do not import their architecture,
  deadlines, schemas, mechanics or scope without a new active decision.
- `docs/CARD_BATTLER_TARGET.md` is the bounded current future-target contract;
  old Character Chronicles deck/board rules are not authoritative for phase 1.
  Existing Card Battler model/code is not evidence of a complete playable game.
- Treat architecture target, active runtime, open POC and archive as four
  different things. Never promote one into another by wording alone.
- When documentation links or paths change, run
  `python scripts/check_documentation.py`. Keep current links resolvable;
  historical missing links in archival source text stay clearly non-operative.

When behavior or architecture changes, update the relevant documents in the
same change:

- `README.md` for user-facing setup or behavior
- `docs/ARCHITECTURE.md` for boundaries and runtime topology
- `docs/CODING_STANDARDS.md` for engineering rules
- `docs/DATA_ARCHITECTURE.md` for persistence and migration semantics
- `docs/REFACTOR_PLAN.md` for migration phase status
- product/status documentation when product scope changes

Documentation describes the actual state. A target architecture must be marked
as a target until it is implemented.

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
