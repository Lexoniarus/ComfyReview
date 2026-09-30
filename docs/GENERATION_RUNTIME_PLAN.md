# Native ComfyUI Generation Runtime Plan

Status: native generation, canonical output collection and explicit
reconciliation are implemented on `refactor/review-boundary`, 2026-09-30.

## Implemented foundation

The canonical database already provides:

- stable generation and image identities;
- optional ComfyUI prompt ID and lifecycle fields;
- raw metadata and workflow provenance;
- workflow hash and normalized sampler stages;
- multiple image output slots per generation;
- optional sidecar paths;
- audited legacy PNG/sidecar import;
- sidecar-independent Review, Ranking, Arena and Curation runtime behavior.

Historical sidecars remain immutable migration evidence. They are not the
target generation runtime.

## Target dependency order

```text
Playground preparation
    -> GenerationPort

GenerationService implements GenerationPort
    -> WorkflowBlueprintRepository
    -> WorkflowCompiler
    -> GenerationRepository
    -> ComfyUiProvider
    -> GenerationOutputCollector
```

Playground selection and prompt rendering are migrated before native generation
but are not wired through a temporary generation facade. Final Playground
submission moves only after the real `GenerationService` exists.

## Workflow blueprint and compiler

A versioned `WorkflowBlueprint` contains an API graph template, explicit role
mappings, expected output-node bindings, sampler-stage definitions and optional
capability requirements.

The `WorkflowCompiler` combines a blueprint with a `GenerationRequest`. It owns
semantic graph mapping for roles such as positive prompt, negative prompt,
checkpoint, sampler stages, reference image and output node. It produces:

```text
CompiledWorkflow
    graph
    graph_hash
    blueprint_uid
    blueprint_version
    resolved_roles
    output_bindings
    sampler_stages
```

Compilation never relies on fixed node IDs, titles or the first matching
KSampler. The current runtime patcher may be used only by an explicit blueprint
migration and is then removed.

Output directory and naming intent come from a `GenerationOutputPolicy` or the
request. The compiler transfers those decisions into mapped graph inputs; it
does not choose them.

## Technical ComfyUI provider

The provider receives only an already compiled graph and exposes technical
operations:

```text
submit(compiled_graph)
get_status(prompt_id)
wait_or_watch(prompt_id)
fetch_outputs(prompt_id)
discover_capabilities()
```

It owns HTTP/WebSocket transport, timeouts, queue/history parsing, technical
job states, capability discovery and typed failures. It has no knowledge of
prompt roles, samplers, catalog entries, output policy or workflow node
semantics.

## Generation lifecycle

```text
prepared -> submitting -> submitted -> running -> completed
                    \-> failed
submitted/running   \-> cancelled
                    \-> reconciliation_required
```

Request, selected prompt revisions, exact rendered prompts and compiled
provenance are persisted in short canonical transactions. No write transaction
is held during external execution. A wait timeout is not a failed generation.
An ambiguous crash between external submit and local confirmation remains
visible for reconciliation. `GenerationReconciliationService` first checks
whether a prior atomic output collection already persisted every compiled
output binding. If so, it safely completes the local lifecycle without relying
on retained ComfyUI history. Otherwise it checks the known prompt in ComfyUI,
repeats output collection idempotently after external completion, and persists
the observed submitted, running, failed or completed state.

An ambiguous `POST /prompt` timeout may leave no local prompt ID. ComfyReview
does not automatically resubmit because that could duplicate a generation. An
operator first identifies the accepted prompt in ComfyUI history or queue and
then associates it explicitly:

```powershell
python -m comfyreview generation reconcile GENERATION_UID --prompt-id PROMPT_ID
```

Once a prompt ID is stored, later attempts can omit `--prompt-id`. Exit code
`0` means the ambiguous state was resolved; exit code `2` means the generation
still requires reconciliation; technical failures return `1`.

## Native output collection

Expected and actual output identity are separate:

```text
CompiledOutputBinding
    role
    node_id

GenerationOutput
    image_uid
    role
    node_id
    output_index
    path
    content_hash
```

The compiler knows the expected role/node binding only. Concrete output indices
are assigned from returned ComfyUI batches during idempotent collection.

## Standard SaveImage cutover

The active `default-character` blueprint uses standard `SaveImage`. Canonical
metadata comes from the request, compiled workflow and collected outputs, with
the actual output index assigned during collection. The former
`name_meta_export` runtime path has been removed; historical sidecar import
remains supported.
