# Native ComfyUI Generation Runtime Plan

Status: canonical image provenance is implemented; native generation remains a
target on `refactor/review-boundary`, 2026-09-30.

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
visible for reconciliation.

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

After native multi-output collection and provenance are verified, blueprints
move to standard `SaveImage` or another explicitly supported native output
node. Canonical metadata comes from the request, compiled workflow and collected
outputs. The `name_meta_export` runtime requirement is removed only after that
cutover; historical sidecar import remains supported.
