# ComfyReview Coding Standards

Status: binding target for all new and changed code from 2026-09-28; canonical
schema-v4 feature cutover implemented 2026-09-30.

The current repository predates this baseline and is not yet fully compliant.
Existing violations are migration work, not precedent for new code.

## 1. Python baseline

- Python >= 3.11.
- PEP 8, four spaces, maximum 79 characters per Python code line.
- `snake_case` for modules/functions/variables.
- `PascalCase` for classes.
- `UPPER_CASE` for constants.
- Public functions and methods have type annotations and concise docstrings.
- Prefer explicit domain types over unstructured dictionaries inside the core.

Mandatory tooling for the quality gate:

- Ruff linting
- Ruff formatting
- mypy
- Pyright (`standard` mode, project-local configuration)
- pytest
- coverage

## 2. Responsibility and function design

A function or method performs one coherent task.

Good separation:

```text
ReviewService.save_review()
  -> validate request
  -> load image
  -> append review event
  -> commit transaction
  -> schedule derived-stat refresh
```

Each named step may be delegated to a focused method/collaborator. The
orchestrator does not embed SQL, HTTP calls, template rendering and filesystem
mutation in one body.

Line count alone does not decide Single Responsibility. Responsibility does.

## 3. Stateful boundaries and OOP

Use classes for objects that own state, resources or external dependencies:

- repositories
- units of work / transaction scopes
- ComfyUI client/provider
- output filesystem provider
- background worker runtime
- long-lived caches
- stateful application services

Use pure functions for deterministic transformations:

- prompt tokenization
- score calculation
- ranking formulas
- normalization
- immutable mapping between domain values

## 4. Dependency Injection

Concrete dependencies are created in the composition root and injected.

Do not do this in a service:

```python
from config import RATINGS_DB_PATH
sqlite3.connect(RATINGS_DB_PATH)
```

Prefer:

```python
class ReviewService:
    def __init__(self, reviews: ReviewRepository, clock: Clock) -> None:
        self._reviews = reviews
        self._clock = clock
```

Configuration values are translated into concrete adapters in bootstrap code.
Business code receives interfaces/ports or typed configuration values.

## 5. Layer boundaries

### Domain

May contain:

- entities
- immutable value objects
- domain validation
- repository/provider ports
- pure domain policies

Must not import:

- `sqlite3`
- FastAPI
- HTTP clients
- Jinja
- concrete filesystem implementations
- concrete ComfyUI clients

### Services

May:

- orchestrate use cases
- coordinate repositories/providers
- manage application-level decisions
- define transaction boundaries through a Unit of Work

Must not:

- execute SQL
- build HTTP requests directly
- read/write arbitrary files directly
- depend on FastAPI request/response objects

### Repositories

Own:

- SQLite SQL
- schema-specific persistence mapping
- queries
- transaction-aware persistence
- database integrity checks

Repositories do not call ComfyUI or render UI.

### Providers

Own external system interaction:

- ComfyUI API
- output folder discovery
- JSON sidecar loading
- file copy/move/delete at explicit workflow boundaries

Providers do not contain business ranking or review rules.

### API / routes

Own:

- HTTP parsing
- validation of transport-level input
- status codes
- response projection
- template selection

Routes call services. They do not execute SQL or external provider calls.

## 6. SQLite rules

- SQL only in repository or explicit offline migration/audit adapters.
- Enable foreign keys for application connections.
- Use parameterized SQL.
- Keep write transactions short.
- Do not await external work while a write transaction is open.
- Related writes are atomic.
- Database connections are always closed, including on exceptions.
- Runtime supports only documented schema versions.
- Unsupported schemas fail explicitly; runtime startup does not silently repair
  arbitrary historical layouts.
- Destructive migration requires backup + explicit offline migration command.
- Schema DDL exists only in the explicit canonical and legacy schema managers;
  architecture tests reject DDL in ordinary repositories, services and routes.
- Normal repositories open existing files in `rw` mode and never create or
  upgrade schemas as a side effect of a query or mutation.
- Known additive legacy repair uses `python -m comfyreview legacy-db upgrade`;
  startup initializes only database files that are completely absent.
- Canonical version changes use the explicit, backed-up
  `python -m comfyreview canonical-db upgrade --output PATH` command. The
  source is not overwritten; startup validates but never performs a version
  cutover. Optional legacy UI-state import is an explicit migration input, not
  a runtime fallback.

## 7. Canonical data vs derived data

Canonical facts are written once and own identity.

Examples:

- prompt/content component
- image/generation record
- review event
- arena comparison
- curation assignment

Derived/rebuildable data:

- image rating aggregates
- prompt atom statistics
- combination statistics
- ranking projections

Rules:

- A derived table/view must have a documented source-of-truth path.
- Do not duplicate complete prompt text per atom/rating when relations can
  express membership.
- Do not persist all theoretical prompt combinations simply because they can be
  computed.
- Prefer views for cheap aggregates. Materialize only when measurement shows a
  real performance need.

## 8. Identity

- Stable IDs identify images, prompts, components and compositions.
- `png_path` and `json_path` are mutable locations, not primary domain identity.
- Moving an image does not require rewriting reviews, comparisons or curation
  records.
- External metadata identifiers are mapped once at the boundary.

## 9. ComfyUI provider rules

- A `WorkflowBlueprintRepository` or equivalent source loads versioned graph
  templates and explicit role mappings.
- A `WorkflowCompiler` maps a `GenerationRequest` and blueprint to an immutable
  compiled API graph. It owns graph semantics but no HTTP or output-naming
  decisions.
- ComfyUI requests live in a provider. The provider receives compiled graphs
  and does not discover prompt, sampler or output roles itself.
- Provider operations use explicit timeouts.
- Submission and completion are separate concepts for long-running work.
- A timed-out wait is not automatically a failed generation.
- Provider errors expose a typed category and preserve actionable diagnostics.
- Services decide what to do with failures; providers do not invent fallback
  generations silently.
- No SQLite write transaction is held across ComfyUI execution.

## 10. Background work

Background jobs have explicit lifecycle states, e.g.:

```text
queued -> running -> completed
                  -> failed
                  -> cancelled
```

Workers:

- consume service-level commands
- do not embed duplicate business rules
- are idempotent where practical
- record bounded error details
- can recover after restart without corrupting canonical data
- are owned by the application lifespan, prevent double-starts and use a
  bounded, visible shutdown timeout

Derived-data rebuilds must be safe to repeat.

## 11. Logging and tracing

Use structured logs with stable event names, for example:

```text
review.saved
generation.submitted
generation.completed
generation.failed
projection.rebuild_started
projection.rebuild_completed
migration.started
migration.completed
```

Where applicable include:

- trace ID
- job ID
- image ID
- generation ID
- duration
- error category

Do not log secrets or entire private prompt payloads by default.

## 12. Testing

- Every stable public Python-core behavior boundary has an explicit behavior
  test and manifest entry.
- Constructors, private delegation methods, trivial accessors and dunder
  methods do not receive separate manifest entries. Complex private domain
  logic is extracted or covered through the public behavior that owns it.
- Target 100% Python-core statement coverage.
- Repositories are tested against temporary SQLite databases.
- Service tests use repository/provider fakes where that isolates behavior.
- Provider unit tests do not require a live ComfyUI server.
- Live ComfyUI integration tests are marked separately.
- Migration tests run on copies/fixtures and verify row counts, relationships,
  invariants and source preservation.
- Architecture tests enforce import/dependency boundaries.

## 13. Frontend

ComfyReview may keep FastAPI + Jinja. A SPA rewrite is not required.

Rules for new/changed frontend code:

- Native ES modules.
- Shared HTTP access via one API client module.
- Views/components do not call `fetch()` directly.
- Dynamic untrusted content is assigned with `textContent`, DOM nodes or safe
  attribute setters, not dynamic HTML strings.
- Stateful components own and release listeners, timers and requests.
- Public module boundaries use JSDoc contracts.
- `checkJs`, ESLint, Prettier and Stylelint belong in the eventual shared gate.

## 14. Quality gate

The repository quality gate is:

```text
python scripts/quality.py
```

The gate runs:

1. Ruff check
2. Ruff format --check
3. mypy
4. Pyright
5. pytest
6. Python-core statement coverage check
7. function-test-manifest check
8. architecture tests
9. frontend lint/format/checkJs tests once frontend modules are introduced

### Legacy ratchet

Repository-wide violations that predate the standards are measured in
`quality/legacy_diagnostics.json`; the corresponding files are listed in
`quality/legacy_python_files.txt`.

Rules:

- the legacy file set may only shrink
- a new diagnostic group or a higher diagnostic count fails the gate
- every new or changed Python file must pass Ruff, formatting, mypy and
  Pyright without a legacy exception
- architecture exceptions may only shrink
- files in `quality/core_scope.txt` require 100% statement coverage
- every discovered public concrete core function or method requires an entry
  in `tests/function_test_manifest.py`

To migrate an existing file, make it fully clean, remove it from the legacy
file list, remove its diagnostic and architecture exceptions, add behavior
tests and update the manifest/core scope where applicable.

Before each intermediate commit, run focused behavior tests and static checks
for every changed file. The targeted gate is a fast feedback mechanism only.
Run the complete gate at the end of every refactor slice and before integration.

The current baseline is not a claim that the full repository already conforms
to the target architecture. It is a versioned inventory that prevents new work
from increasing known debt.
