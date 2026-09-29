# Legacy Output Import

Status: Slice 3A audit-only preparation.

## Purpose

Historical PNG files and custom-node JSON sidecars are preserved as migration
sources. Before any write import is attempted, ComfyReview runs a read-only
audit against the current output tree and canonical database.

Run:

```text
python -m comfyreview legacy-output audit
```

Optional overrides:

```text
python -m comfyreview legacy-output audit   --output-root <path>   --database <path>   --report <path>
```

The default report is `data/reports/legacy-output-audit.json`.

## What the audit verifies

For every PNG below the output root, excluding `_trash` and `_lora_export`, the
audit records:

- whether a matching JSON sidecar exists and parses as an object
- SHA-256 fingerprints for the PNG and sidecar
- the stored `comfy_prompt_graph` / `prompt_graph` hash
- a candidate legacy generation group derived from timestamp plus graph hash
- every standard `KSampler` stage in graph order
- sampler-like nodes that are not standard `KSampler`
- checkpoint and LoRA references from the graph
- prompt fingerprints without copying prompt text into the report
- graph-vs-sidecar conflicts
- whether the PNG already has a live canonical image identity

The audit does not modify PNGs, JSON sidecars, ratings or the canonical
database.

## Source-of-truth policy

For the later write import:

- the stored ComfyUI graph is historical render truth when present
- top-level custom-node metadata is compatibility evidence
- disagreements are reported rather than silently overwritten
- raw sidecars remain untouched and will be retained as provenance
- existing canonical image/generation identities are enriched rather than
  duplicated
- historical review scores may be intentionally omitted

Slice 3B will implement the write importer only after the audit report has been
reviewed.
