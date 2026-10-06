# Native ComfyUI Generation Runtime Plan

Status: native generation, canonical output collection, explicit
reconciliation, the owned lifecycle worker and AnimeSharp Blueprint v4 are
implemented, 2026-10-06.

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
checkpoint, sampler stages, reference image, output width/height and output
node. It produces:

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

## Blueprint v4 output geometry and upscaling

Profiles are not part of the active generation flow. The browser sends a
format/orientation (`2:3`, `3:2`, `16:9`, `9:16`, `1:1`) and output class
(`720`, `1080`, `2160`). The geometry policy resolves both a validated latent
canvas and one of the 15 fixed target dimensions without crop before
persistence.

The default-character v4 graph fixes this path:

```text
VAEDecode
  -> UpscaleModelLoader(example-upscaler.pth)
  -> ImageUpscaleWithModel
  -> ImageSharpen(radius=4, sigma=0.1, alpha=0.03)
  -> ImageScale(lanczos, crop=disabled, output_width/output_height)
  -> SaveImage
```

Capability discovery includes upscale models. Missing required nodes or the
fixed model produces a typed application failure before a generation row is
created or a graph is submitted. The provider remains unaware of semantic
roles and receives only the compiled graph.

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

The application lifespan owns one `GenerationLifecycleWorker`. After schema
validation it immediately runs a bounded recovery/observation pass and then
polls every two seconds. `prepared` work left by a stopped local process is
failed without contacting ComfyUI; `submitting` work is marked ambiguous and is
never sent again. `submitted` and `running` jobs use the same status mapping and
output collector as an explicit wait. Connection failures and timeouts are
retryable observations, not job failures, while an unknown prompt ID becomes
`reconciliation_required`.

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

When ComfyUI no longer retains a known prompt, that explicit reconcile action
may inspect the persisted output subdirectory and exact filename prefix. It
accepts only one PNG matching the single expected output binding and routes it
through the ordinary output/hash/geometry collector. No automatic worker pass
uses this filesystem fallback, and no similar-name heuristic or resubmission is
allowed.

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
