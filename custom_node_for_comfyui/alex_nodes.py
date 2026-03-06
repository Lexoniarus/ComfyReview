# alex_nodes.py
# custom nodes: name_meta_export
#
# ZIEL
# 1) PNG speichern
# 2) Sidecar JSON speichern mit Schema, das ComfyReview erwartet
# 3) PNG Basisname und JSON Basisname sind identisch
# 4) Source of Truth kommt aus dem Prompt Graph
#    chosen_line ist optional und nur noch Kompatibilitaet
#
import os
import json
import copy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

try:
    import torch
except Exception:
    torch = None  # type: ignore

try:
    import numpy as np
except Exception:
    np = None  # type: ignore

try:
    from PIL import Image
except Exception:
    Image = None  # type: ignore

try:
    import folder_paths
except Exception:
    folder_paths = None  # type: ignore


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_mkdir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    try:
        return str(x)
    except Exception:
        return ""


def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _as_filename_base(s: str) -> str:
    s = (s or "").strip()
    for ch in ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]:
        s = s.replace(ch, "_")
    s = s.replace(" ", "")
    return s


def _format_cfg(cfg: float) -> str:
    f = float(cfg)
    if abs(f - round(f)) < 1e-6:
        return str(int(round(f)))
    return f"{f:.2f}".rstrip("0").rstrip(".")


def _parse_chosen_line(line: str) -> Tuple[str, str, int, float, Optional[int]]:
    parts = [p.strip() for p in (line or "").split(",") if p.strip() != ""]
    if len(parts) not in (4, 5):
        raise ValueError(
            "name_meta_export: chosen_line ungültig, erwartet "
            "'sampler,scheduler,steps,cfg' oder 'sampler,scheduler,steps,cfg,seed'"
        )

    sampler = parts[0]
    scheduler = parts[1]

    try:
        steps = int(parts[2])
    except Exception:
        raise ValueError(f"name_meta_export: steps ist nicht int-like: {parts[2]!r}")

    try:
        cfg = float(parts[3])
    except Exception:
        raise ValueError(f"name_meta_export: cfg ist nicht float-like: {parts[3]!r}")

    seed_used: Optional[int] = None
    if len(parts) == 5:
        try:
            seed_used = int(parts[4])
        except Exception:
            raise ValueError(f"name_meta_export: seed ist nicht int-like: {parts[4]!r}")

    if not sampler or not scheduler:
        raise ValueError("name_meta_export: sampler oder scheduler ist leer")

    return sampler, scheduler, steps, cfg, seed_used


def _coerce_batch(images) -> List[Any]:
    if torch is not None and isinstance(images, torch.Tensor):
        if images.ndim == 3:
            return [images]
        if images.ndim == 4:
            return [images[i] for i in range(images.shape[0])]
        raise ValueError(f"name_meta_export: IMAGE torch shape unsupported: {tuple(images.shape)}")

    if np is not None and isinstance(images, np.ndarray):
        if images.ndim == 3:
            return [images]
        if images.ndim == 4:
            return [images[i] for i in range(images.shape[0])]
        raise ValueError(f"name_meta_export: IMAGE numpy shape unsupported: {tuple(images.shape)}")

    if isinstance(images, (list, tuple)):
        if len(images) == 0:
            raise ValueError("name_meta_export: images list ist leer")
        return list(images)

    raise ValueError(f"name_meta_export: unsupported images type: {type(images)}")


def _tensor_to_pil(img_t) -> "Image.Image":
    if Image is None or np is None:
        raise RuntimeError("name_meta_export: PIL und numpy werden benötigt")

    if torch is not None and isinstance(img_t, torch.Tensor):
        t = img_t
        if t.ndim == 4:
            t = t[0]
        if t.ndim != 3:
            raise ValueError(f"name_meta_export: torch image shape unsupported: {tuple(t.shape)}")

        img = t.detach().cpu()

        if img.dtype != torch.uint8:
            img = (img.clamp(0, 1) * 255.0).round().to(torch.uint8)

        arr = img.numpy()

    elif np is not None and isinstance(img_t, np.ndarray):
        arr = img_t
        if arr.ndim == 4:
            arr = arr[0]
        if arr.ndim != 3:
            raise ValueError(f"name_meta_export: numpy image shape unsupported: {tuple(arr.shape)}")
        if arr.dtype != np.uint8:
            if np.issubdtype(arr.dtype, np.floating):
                arr = np.clip(arr, 0.0, 1.0)
                arr = (arr * 255.0).round().astype(np.uint8)
            else:
                arr = arr.astype(np.uint8)
    else:
        raise ValueError(f"name_meta_export: unsupported image type: {type(img_t)}")

    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L")
    if arr.shape[-1] == 1:
        return Image.fromarray(arr[:, :, 0], mode="L")
    if arr.shape[-1] == 3:
        return Image.fromarray(arr, mode="RGB")
    if arr.shape[-1] == 4:
        return Image.fromarray(arr, mode="RGBA")

    raise ValueError(f"name_meta_export: channel count unsupported: {arr.shape[-1]}")


def _find_first_node(prompt: Dict[str, Any], class_type_lower: str) -> Optional[Dict[str, Any]]:
    for _nid, node in prompt.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type") or node.get("type")
        if ct is None:
            continue
        if str(ct).strip().lower() == class_type_lower:
            return node
    return None


def _extract_checkpoint_from_prompt(prompt: Dict[str, Any]) -> str:
    ck_node = _find_first_node(prompt, "checkpointloadersimple") or _find_first_node(prompt, "checkpointloader")
    if not ck_node:
        return ""
    inputs = ck_node.get("inputs") or {}
    if not isinstance(inputs, dict):
        return ""
    ck = inputs.get("ckpt_name")
    if isinstance(ck, str) and ck.strip():
        return ck.strip()
    return ""


def _extract_ksampler_inputs(prompt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Liest die finalen Werte aus dem ersten KSampler.
    Das ist ab jetzt die Render Wahrheit.

    Erwartete Inputs im Prompt Graph:
    - seed
    - steps
    - cfg
    - sampler_name
    - scheduler
    - denoise
    """
    ks = _find_first_node(prompt, "ksampler")
    if not ks:
        return {
            "seed": 0,
            "steps": 0,
            "cfg": 0.0,
            "sampler_name": "",
            "scheduler": "",
            "denoise": 1.0,
        }

    inputs = ks.get("inputs") or {}
    if not isinstance(inputs, dict):
        return {
            "seed": 0,
            "steps": 0,
            "cfg": 0.0,
            "sampler_name": "",
            "scheduler": "",
            "denoise": 1.0,
        }

    return {
        "seed": _as_int(inputs.get("seed"), 0),
        "steps": _as_int(inputs.get("steps"), 0),
        "cfg": _as_float(inputs.get("cfg"), 0.0),
        "sampler_name": _safe_str(inputs.get("sampler_name")).strip(),
        "scheduler": _safe_str(inputs.get("scheduler")).strip(),
        "denoise": _as_float(inputs.get("denoise"), 1.0),
    }


def _extract_prompt_strings(prompt_graph: Dict[str, Any]) -> Tuple[str, str]:
    pos = ""
    neg = ""

    for _nid, node in prompt_graph.items():
        if not isinstance(node, dict):
            continue
        ct = _safe_str(node.get("class_type") or node.get("type")).lower()
        if ct not in ("primitivestringmultiline", "primitivestring"):
            continue

        meta = node.get("_meta") or {}
        title = _safe_str(meta.get("title")).strip().lower()

        inputs = node.get("inputs") or {}
        if not isinstance(inputs, dict):
            continue

        v = inputs.get("value")
        if v is None:
            v = inputs.get("text")
        if not isinstance(v, str):
            continue

        if title == "prompt" and not pos:
            pos = v
        if (title == "negative prompt" or title == "negativeprompt") and not neg:
            neg = v

    if not pos:
        node = prompt_graph.get("26:24")
        if isinstance(node, dict):
            ins = node.get("inputs") or {}
            if isinstance(ins, dict):
                v = ins.get("value") or ins.get("text")
                if isinstance(v, str):
                    pos = v

    if not neg:
        node = prompt_graph.get("25:24")
        if isinstance(node, dict):
            ins = node.get("inputs") or {}
            if isinstance(ins, dict):
                v = ins.get("value") or ins.get("text")
                if isinstance(v, str):
                    neg = v

    return pos, neg


class name_meta_export:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "subdir": ("STRING", {"default": ""}),
            },
            "optional": {
                "chosen_line": ("STRING", {"default": ""}),
                "ckpt_name": ("STRING", {"default": ""}),
                "output_root": ("STRING", {"default": ""}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save"
    OUTPUT_NODE = True
    CATEGORY = "alex_nodes"

    def save(
        self,
        images,
        subdir: str,
        chosen_line: str = "",
        ckpt_name: str = "",
        output_root: str = "",
        prompt: Optional[Dict[str, Any]] = None,
        extra_pnginfo: Optional[Dict[str, Any]] = None,
    ):
        if prompt is None or not isinstance(prompt, dict):
            raise ValueError("name_meta_export: missing prompt graph (PROMPT)")

        # prompt_graph fuer JSON kopieren und optional KSampler inputs patchen (nur fuer Konsistenz)
        prompt_store = prompt
        try:
            prompt_store = copy.deepcopy(prompt)
        except Exception:
            prompt_store = prompt

        # checkpoint
        ckpt_used = (ckpt_name or "").strip()
        if not ckpt_used:
            ckpt_used = _extract_checkpoint_from_prompt(prompt_store)

        model_base = Path(ckpt_used).name if ckpt_used else "unknown_checkpoint"
        if model_base.lower().endswith(".safetensors"):
            model_base = model_base[:-11]
        elif model_base.lower().endswith(".ckpt"):
            model_base = model_base[:-5]
        model_base = _as_filename_base(model_base)

        # Source of Truth fuer KSampler Werte
        ks_in = _extract_ksampler_inputs(prompt_store)

        sampler_used = ks_in["sampler_name"]
        scheduler_used = ks_in["scheduler"]
        steps_used = int(ks_in["steps"])
        cfg_used = float(ks_in["cfg"])
        seed_used = int(ks_in["seed"])
        denoise = float(ks_in["denoise"])

        # Kompatibilitaet: wenn chosen_line mitgeliefert wird, darf sie seed ueberschreiben
        line_raw = (chosen_line or "").strip()
        if line_raw:
            sampler_l, scheduler_l, steps_l, cfg_l, seed_from_line = _parse_chosen_line(line_raw)
            sampler_used = sampler_l
            scheduler_used = scheduler_l
            steps_used = int(steps_l)
            cfg_used = float(cfg_l)
            if seed_from_line is not None:
                seed_used = int(seed_from_line)

        # chosen_line im JSON bleibt exakt wie bisher: ohne seed
        line_canon = f"{sampler_used},{scheduler_used},{steps_used},{cfg_used}"

        ks = {
            "seed": seed_used,
            "steps": steps_used,
            "cfg": cfg_used,
            "sampler": sampler_used,
            "scheduler": scheduler_used,
            "denoise": denoise,
        }

        # output dir
        root = (output_root or "").strip()
        if root == "":
            if folder_paths is not None:
                root = folder_paths.get_output_directory()
            else:
                root = os.getcwd()

        sub = (subdir or "").strip()
        out_dir = os.path.join(root, sub) if sub else root
        _safe_mkdir(out_dir)

        ts = _now_ts()

        base = (
            f"{model_base}_{ks['sampler']}_{ks['scheduler']}_{ks['steps']}"
            f"_cfg{_format_cfg(ks['cfg'])}_seed{ks['seed']}_{ts}"
        )

        batch_list = _coerce_batch(images)

        pos_prompt, neg_prompt = _extract_prompt_strings(prompt_store)

        ui_images = []

        for i, img in enumerate(batch_list):
            suffix = "" if len(batch_list) == 1 else f"_{i}"
            file_base = f"{base}{suffix}"

            png_path = os.path.join(out_dir, f"{file_base}.png")
            json_path = os.path.join(out_dir, f"{file_base}.json")

            pil = _tensor_to_pil(img)
            pil.save(png_path)

            meta = {
                "timestamp": ts,
                "checkpoint": _safe_str(ckpt_used),
                "model_base": model_base,
                "ksampler": {
                    "seed": ks["seed"],
                    "steps": ks["steps"],
                    "cfg": ks["cfg"],
                    "sampler": ks["sampler"],
                    "scheduler": ks["scheduler"],
                    "denoise": ks["denoise"],
                },
                "chosen_line": line_canon,
                "pos_prompt": pos_prompt,
                "neg_prompt": neg_prompt,
                "comfy_prompt_graph": prompt_store,
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            ui_images.append(
                {
                    "filename": os.path.basename(png_path),
                    "subfolder": subdir.strip() if subdir else "",
                    "type": "output",
                }
            )

        return {"ui": {"images": ui_images}, "result": (images,)}


NODE_CLASS_MAPPINGS = {
    "name_meta_export": name_meta_export,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "name_meta_export": "name_meta_export",
}