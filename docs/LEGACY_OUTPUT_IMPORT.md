# Legacy Output Import

Status: Slice 3A audit and Slice 3B explicit import implemented.

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
database. Its report is a snapshot contract: summary counts and item evidence
must still match when the importer starts.

## Explicit import

Run the write phase only while the application is stopped:

```text
python -m comfyreview legacy-output import
```

The command accepts `--report` and `--backup-dir` overrides. Before opening a
write transaction it validates the report structure, canonical database path,
existing UID assignments and output-slot ownership. It then recalculates PNG,
sidecar and workflow hashes from the source files. A changed source, conflict,
partial graph, unsupported sampler, missing file or identity collision aborts
the complete import.

Existing image and generation UIDs are retained. Existing generations may be
enriched with historical workflow, raw metadata, prompts, checkpoint, LoRAs
and sampler stages, but the importer does not replace source, lifecycle state,
ComfyUI prompt ID, timestamps or occupied output slots. New identities are
derived from content evidence rather than paths. PNGs without a sidecar remain
excluded and are reported separately.

The importer emits the SQLite backup path before its first write and performs
all canonical writes in one transaction. An ordinary write failure rolls the
transaction back and validates the database. The backup is restored only when
post-rollback validation fails or the commit state cannot be established
safely. Restore failures are reported separately from the original import
failure. Source PNGs and sidecars are never modified.

## Source-of-truth policy

For the write import:

- the stored ComfyUI graph is historical render truth when present
- top-level custom-node metadata is compatibility evidence
- disagreements are reported rather than silently overwritten
- raw sidecars remain untouched and will be retained as provenance
- existing canonical image/generation identities are enriched rather than
  duplicated
- historical review scores are outside this provenance import and move through
  the separate canonical review cutover

Audit reports, backups and runtime databases are local operational artifacts;
they are not committed.
