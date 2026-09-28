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
  combinations. Persist combinations when they are used, generated, curated or
  otherwise become domain-relevant.
- Schema changes are explicit and versioned. Runtime startup must not silently
  mutate an unknown or unsupported database into a new schema.
- Existing databases are never destructively migrated without a backup and an
  explicit migration command.

## ComfyUI integration

- ComfyUI is an external provider, not part of the domain layer.
- Workflow submission, job polling, output collection and capability discovery
  belong to the ComfyUI provider boundary.
- Long-running ComfyUI jobs are modeled as asynchronous work. A client timeout
  is not equivalent to a failed generation.
- Generated image identity and generation metadata must remain reproducible
  even if output files are moved later.
- The repository-specific ComfyUI metadata export node remains a technical
  integration boundary; its payload must be mapped into canonical domain data.

## Tests and quality

- No new concrete Python-Core callable is accepted without an explicit behavior
  test.
- Maintain a function-to-test manifest for the Python core. New core functions
  and methods must be registered there with a counter-test.
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
- The shared quality gate must run formatting, linting, typing, tests, coverage
  and architecture checks before integration.

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
