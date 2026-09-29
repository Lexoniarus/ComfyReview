# Native ComfyUI Generation Runtime Plan

Status: agreed implementation direction for `refactor/review-boundary`.
Slice 2A is based on commit
`09d2b8aacf75cb8742f88fb58fb9686b17705eaf`.

## Goal

Move ComfyReview from a custom-node/sidecar-centered generation model to a
canonical generation-run model driven by the native ComfyUI API while
preserving all existing generated PNG files and JSON sidecars as migration
sources.

The submitted ComfyUI API graph becomes the render provenance source of truth.
Normalized fields remain query conveniences and learning dimensions, not a
second independent truth.

## Slice 1 - canonical generation provenance

Implemented:

- canonical schema version 2
- explicit backed-up v1 -> v2 upgrade
- raw metadata/workflow provenance columns on `generations`
- ComfyUI `prompt_id` slot and lifecycle timestamps/status
- `generation_sampler_stages` for multiple KSampler stages

## Slice 2A - output identity schema

Implemented by schema version 3:

- one generation may own multiple image outputs
- image identity is independent from generation identity
- output slots use `output_node_id` plus `output_index`
- `json_path` is optional canonical provenance
- delete tombstones are keyed by image identity
- v2 live images, reviews and deleted tombstones migrate without changing IDs
- v1 can still upgrade directly to the current schema

The existing sidecar-backed runtime remains active for this commit.

## Slice 2B - sidecar-independent runtime image index

Next:

- make the canonical database the runtime image index
- add typed image reads by stable `image_uid`
- allow native ComfyUI outputs with no JSON sidecar to enter Review/Top/Arena
- keep filesystem PNG/sidecar discovery as a legacy import path
- stop treating the existence of a matching `.json` file as live-image
  identity

## Slice 3 - legacy PNG/sidecar importer

Build an explicit offline/import service for existing generated images.

For every valid PNG/JSON pair:

1. preserve the PNG unchanged
2. retain the raw sidecar payload as provenance
3. prefer `comfy_prompt_graph` / `prompt_graph` as historical workflow truth
4. normalize exact positive and negative prompts
5. normalize checkpoint and LoRA information
6. extract every KSampler node into `generation_sampler_stages`
7. record conflicts between graph values and legacy summary values
8. create canonical generation and image identities

Historical ratings may intentionally be omitted. Old sidecars remain untouched.

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

The provider owns HTTP submission, WebSocket execution events, queue/history
retrieval, capability discovery and typed provider failures.

## Slice 5 - workflow compiler

Replace fixed-node patching with semantic workflow roles for prompts,
checkpoints, sampler stages, LoRAs, reference images/adapters and output nodes.
Store the compiled graph, its hash, blueprint/version and role mapping before
submission.

## Slice 6 - custom-node removal

After native generation provenance is verified against real outputs, replace
`name_meta_export` with standard ComfyUI output nodes. Keep old custom-node
sidecars supported only by the legacy importer. The canonical database becomes
the ComfyReview source of truth; ComfyUI history and PNG metadata are execution
or portable evidence.
