from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


RequestJson = Callable[[str, str, Optional[dict], int], Any]


def _dedupe_sorted(values: List[str]) -> List[str]:
    out = [str(x).strip() for x in values if str(x).strip()]
    return sorted(set(out), key=lambda s: s.lower())


def get_from_object_info(request_json: RequestJson, *, input_key: str) -> List[str]:
    """Extract KSampler options from /object_info."""
    try:
        r = request_json("GET", "/object_info", None, 20)
        if not r.ok or not isinstance(r.response_json, dict):
            return []

        ks = r.response_json.get("KSampler")
        if not isinstance(ks, dict):
            return []

        inputs = ks.get("input")
        if not isinstance(inputs, dict):
            return []

        req = inputs.get("required")
        opt = inputs.get("optional")

        container = None
        if isinstance(req, dict) and input_key in req:
            container = req.get(input_key)
        elif isinstance(opt, dict) and input_key in opt:
            container = opt.get(input_key)

        values: List[str] = []
        if isinstance(container, list) and container:
            if isinstance(container[0], list):
                values = container[0]
            else:
                values = container

        return _dedupe_sorted([str(x) for x in values])
    except Exception:
        return []


def get_samplers(request_json: RequestJson) -> List[str]:
    samplers = get_from_object_info(request_json, input_key="sampler_name")
    if samplers:
        return samplers

    try:
        r = request_json("GET", "/samplers", None, 20)
        if r.ok and isinstance(r.response_json, list):
            return [str(x) for x in r.response_json if str(x).strip()]
    except Exception:
        pass
    return []


def get_schedulers(request_json: RequestJson) -> List[str]:
    schedulers = get_from_object_info(request_json, input_key="scheduler")
    if schedulers:
        return schedulers

    try:
        r = request_json("GET", "/schedulers", None, 20)
        if r.ok and isinstance(r.response_json, list):
            return [str(x) for x in r.response_json if str(x).strip()]
    except Exception:
        pass
    return []


def get_checkpoints(
    request_json: RequestJson,
    *,
    checkpoints_dir: Path,
) -> List[str]:
    """Try to obtain checkpoints list, with local fallback."""

    # 1) /object_info (preferred)
    try:
        r = request_json("GET", "/object_info", None, 20)
        if r.ok and isinstance(r.response_json, dict):
            for cls in (
                "CheckpointLoaderSimple",
                "CheckpointLoader",
                "RandomLoadCheckpoint",
                "CheckpointLoaderSimpleAdvanced",
            ):
                info = r.response_json.get(cls)
                if not isinstance(info, dict):
                    continue
                inp = info.get("input")
                if not isinstance(inp, dict):
                    continue
                required = inp.get("required") if isinstance(inp.get("required"), dict) else {}
                optional = inp.get("optional") if isinstance(inp.get("optional"), dict) else {}

                container = None
                if "ckpt_name" in required:
                    container = required.get("ckpt_name")
                elif "ckpt_name" in optional:
                    container = optional.get("ckpt_name")

                values: List[str] = []
                if isinstance(container, list) and container:
                    if isinstance(container[0], list):
                        values = container[0]
                    else:
                        values = container

                out = _dedupe_sorted([str(x) for x in values])
                if out:
                    return out
    except Exception:
        pass

    # 2) /models/checkpoints
    try:
        r = request_json("GET", "/models/checkpoints", None, 20)
        if r.ok and isinstance(r.response_json, list):
            out: List[str] = []
            for item in r.response_json:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("name")
                    if isinstance(name, str) and name.strip():
                        out.append(name.strip())
            out = _dedupe_sorted(out)
            if out:
                return out
    except Exception:
        pass

    # 3) local filesystem fallback
    try:
        base = Path(checkpoints_dir)
        if base.exists():
            out: List[str] = []
            for ext in (".safetensors", ".ckpt", ".pt"):
                for p in base.rglob(f"*{ext}"):
                    if not p.is_file():
                        continue
                    rel = str(p.relative_to(base)).replace("\\", "/")
                    out.append(rel)
            return _dedupe_sorted(out)
    except Exception:
        pass

    return []
