from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .format_detection import is_api_prompt_format, iter_nodes


def patch_workflow_for_run(
    workflow: Dict[str, Any],
    *,
    positive_prompt: str,
    negative_prompt: str,
    subdir: str,
    checkpoint: Optional[str] = None,
    seed: Optional[int] = None,
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    sampler: Optional[str] = None,
    scheduler: Optional[str] = None,
    denoise: Optional[float] = None,
) -> Dict[str, Any]:
    """Return patched API prompt workflow for one run.

    Semantik ist kompatibel zur vorherigen ComfyClient.patch_workflow_for_run.
    """

    wf: Dict[str, Any] = json.loads(json.dumps(workflow))

    if not is_api_prompt_format(wf):
        return wf

    pos = str(positive_prompt or "")
    neg = str(negative_prompt or "")

    def _patch_primitive_value(node: Dict[str, Any], value: str) -> bool:
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            return False
        if "value" in inputs:
            inputs["value"] = value
            return True
        if "text" in inputs:
            inputs["text"] = value
            return True
        return False

    patched_pos = False
    patched_neg = False

    # Fixed node IDs (current known setup)
    node_pos = wf.get("26:24")
    if isinstance(node_pos, dict) and str(node_pos.get("class_type", "")).lower() in (
        "primitivestringmultiline",
        "primitivestring",
    ):
        patched_pos = _patch_primitive_value(node_pos, pos)

    node_neg = wf.get("25:24")
    if isinstance(node_neg, dict) and str(node_neg.get("class_type", "")).lower() in (
        "primitivestringmultiline",
        "primitivestring",
    ):
        patched_neg = _patch_primitive_value(node_neg, neg)

    # Fallback by _meta.title
    if not patched_pos or not patched_neg:
        for _nid, node in iter_nodes(wf):
            ct = str(node.get("class_type", "")).strip().lower()
            if ct not in ("primitivestringmultiline", "primitivestring"):
                continue
            meta = node.get("_meta") or {}
            title = str(meta.get("title", "")).strip().lower()
            if not patched_pos and title == "prompt":
                patched_pos = _patch_primitive_value(node, pos)
            if not patched_neg and title in ("negative prompt", "negativeprompt"):
                patched_neg = _patch_primitive_value(node, neg)

    # Subdir patch (name_meta_export)
    for _nid, node in iter_nodes(wf):
        if str(node.get("class_type", "")).strip().lower() != "name_meta_export":
            continue
        inputs = node.get("inputs")
        if isinstance(inputs, dict):
            inputs["subdir"] = str(subdir or "")
        break

    # Checkpoint patch
    if checkpoint is not None:
        ckpt = str(checkpoint or "").strip()
        if ckpt:
            for _nid, node in iter_nodes(wf):
                ct = str(node.get("class_type", "")).strip().lower()
                if ct in ("randomloadcheckpoint", "checkpointloadersimple", "checkpointloader"):
                    inputs = node.get("inputs")
                    if isinstance(inputs, dict) and "ckpt_name" in inputs:
                        inputs["ckpt_name"] = ckpt
                        break

    # KSampler patch
    def _patch_ksampler(node: Dict[str, Any]) -> None:
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            return
        if seed is not None:
            inputs["seed"] = int(seed)
        if steps is not None:
            inputs["steps"] = int(steps)
        if cfg is not None:
            inputs["cfg"] = float(cfg)
        if sampler is not None and str(sampler).strip():
            inputs["sampler_name"] = str(sampler).strip()
        if scheduler is not None and str(scheduler).strip():
            inputs["scheduler"] = str(scheduler).strip()
        if denoise is not None:
            inputs["denoise"] = float(denoise)

    for _nid, node in iter_nodes(wf):
        if str(node.get("class_type", "")).strip().lower() == "ksampler":
            _patch_ksampler(node)
            break

    return wf
