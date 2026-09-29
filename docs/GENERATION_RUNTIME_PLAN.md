# Native ComfyUI Generation Runtime Plan

Status: agreed implementation direction for `refactor/review-boundary`.
Base reviewed at commit `0270fd8ebf8ba81eb2e3f1eaa1775a40d9d7c15e`.

## Goal

Move ComfyReview from a custom-node/sidecar-centered generation model to a
canonical generation-run model driven by the native ComfyUI API while
preserving all existing generated PNG files and their legacy JSON sidecars as
migration sources.

The submitted ComfyUI API graph becomes the render provenance source of truth.
Normalized fields remain query conveniences and learning dimensions, not a
second independent truth.

## Slice 1 - canonical generation provenance

Implemented by this change:

- canonical schema version 2
- explicit backed-up v1 -> v2 upgrade
- raw metadata/workflow provenance columns on `generations`
- ComfyUI `prompt_id` slot and lifecycle timestamps/status
- `generation_sampler_stages` for multiple KSampler stages
- no runtime submission behavior change yet

This slice intentionally keeps the current image/sidecar review boundary
working exactly as before.

## Slice 2 - output identity and sidecar independence

Change the canonical output model so that:

- one generation can own multiple output images
- an image has its own stable identity
- `json_path` becomes optional legacy provenance
- new native ComfyUI outputs do not require a sidecar to be reviewable
- delete/restore tombstones operate on image identity rather than assuming one
  image per generation

The current filesystem catalog remains available for legacy discovery/import,
but the canonical database becomes the runtime image index.

## Slice 3 - legacy PNG/sidecar importer

Build an explicit offline/import service for existing generated images.

For every valid PNG/JSON pair:

1. preserve the PNG unchanged
2. retain the raw sidecar payload as provenance
3. prefer `comfy_prompt_graph` / `prompt_graph` as historical workflow truth
4. normalize exact positive and negative prompts
5. normalize checkpoint and LoRA information
6. extract every KSampler node into `generation_sampler_stages`
7. record conflicts between graph values and legacy top-level summary values
   instead of silently choosing the summary
8. create canonical generation and image identities

Historical ratings may be omitted from this import when intentionally discarded.
The old sidecar files remain untouched after import.

## Slice 4 - native ComfyUI provider and generation service

Introduce the target runtime boundary:

```text
GenerationService
    -> persist prepared GenerationRun
    -> ComfyUiProvider.submit(final_graph)
    -> store comfy_prompt_id
    -> watch native ComfyUI execution outside SQLite write transactions
    -> fetch final outputs/history
    -> persist output images atomically
```

The provider owns:

- HTTP submission
- native WebSocket execution events
- queue/history/output retrieval
- capability discovery
- typed provider errors and timeouts

A wait timeout must not be treated as proof that ComfyUI failed the job.

## Slice 5 - workflow compiler

Replace the current fixed-node patching model with semantic workflow roles.

The compiler should operate on intent such as:

- positive prompt
- negative prompt
- checkpoint
- primary/base sampler
- optional refiner/detail sampler stages
- LoRA stack
- reference image / adapter bindings
- output nodes

The compiled graph, its hash, blueprint/version information and role-to-node
mapping are stored with the generation run before submission.

## Slice 6 - custom-node removal from the default runtime

After native generation provenance is verified against real outputs:

- replace `name_meta_export` with standard ComfyUI output nodes
- stop requiring installation of the repository custom node
- keep custom-node sidecars supported only by the legacy importer
- retain normal ComfyUI PNG metadata as a portable fallback when enabled

At this point the canonical database is the ComfyReview source of truth,
ComfyUI history is execution evidence, and PNG metadata/old sidecars are
portable or historical provenance rather than mandatory runtime state.
