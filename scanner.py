# scanner.py
#
# WAS IST DAS?
# Dateisystem Scanner fuer ComfyReview.
# Findet PNG Dateien und deren Sidecar JSON Meta Dateien.
# Baut daraus Item Objekte, die spaeter in die DB geschrieben oder im UI angezeigt werden.
#
# WO KOMMT ES HER?
# Input ist das Output Verzeichnis von ComfyUI (OUTPUT_ROOT) plus optional ein Trash Verzeichnis.
# Meta Informationen kommen aus der Sidecar JSON Datei, die deine Custom Node name_meta_export schreibt.
#
# WO GEHT ES HIN?
# Output ist eine Liste Item, die von Services oder Routern genutzt wird.
# move_to_trash verschiebt PNG und JSON im Dateisystem in den Trash Ordner.
#
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set


# WAS IST DAS?
# Reines Transport Objekt fuer einen gefundenen Output Datensatz.
# png_path und json_path sind Dateisystem Pfade.
# subdir ist relativ zum Output Root.
# model_branch checkpoint combo_key sind Normalisierungen fuer UI Filter und DB Gruppierung.
# meta ist die komplette JSON Struktur.
@dataclass
class Item:
    png_path: Path
    json_path: Path
    subdir: str
    model_branch: str
    checkpoint: str
    combo_key: str
    meta: Dict[str, Any]


def _safe_read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}


def _normalize_exts(exts: Set[str]) -> Set[str]:
    out: Set[str] = set()
    for e in (exts or set()):
        e2 = str(e or "").strip().lower()
        if not e2:
            continue
        if not e2.startswith("."):
            e2 = f".{e2}"
        out.add(e2)
    return out or {".png"}


def _iter_files_by_exts(root: Path, exts: Set[str]) -> Iterable[Path]:
    exts_n = _normalize_exts(exts)
    for ext in sorted(exts_n):
        yield from root.rglob(f"*{ext}")


def _sidecar_json_path(png_path: Path) -> Path:
    return png_path.with_suffix(".json")


def _infer_subdir(png_path: Path, root: Path) -> str:
    """Infer subdir for UI scope.

    vNext rule:
    - Playground scope is the Character folder: playground/<Character>
    - Files may live in deeper set folders (scene/outfit/...), but subdir stays the character.

    For non-playground folders, we keep the full relative parent path.
    """

    try:
        rel_dir = png_path.parent.relative_to(root)
        parts = [p for p in rel_dir.parts if p]
        if len(parts) >= 2 and str(parts[0]).lower() == "playground":
            # ignore deeper set folders for scope
            return f"playground/{parts[1]}"
        return str(rel_dir).replace("\\", "/")
    except Exception:
        return str(png_path.parent.name)


def _ckpt_from_graph_node(node: Dict[str, Any]) -> str:
    if not isinstance(node, dict):
        return ""

    ct = node.get("class_type")
    if ct not in (
        "CheckpointLoaderSimple",
        "CheckpointLoader",
        "RandomLoadCheckpoint",
        "RandomLoadCheckpointSimple",
    ):
        return ""

    inputs = node.get("inputs") or {}
    ck = inputs.get("ckpt_name") or inputs.get("checkpoint") or inputs.get("ckpt") or ""
    if ck and not isinstance(ck, list):
        return str(ck)
    return ""


def _infer_checkpoint(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return "unknown"

    ck = meta.get("checkpoint") or meta.get("ckpt_name") or meta.get("ckpt") or ""
    if ck:
        return str(ck)

    try:
        g = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
        for _, node in (g or {}).items():
            if not isinstance(node, dict):
                continue
            ck2 = _ckpt_from_graph_node(node)
            if ck2:
                return ck2
    except Exception:
        pass

    return "unknown"


def _infer_model_branch(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return "unknown"

    v = (
        meta.get("model_branch")
        or meta.get("model_base")
        or meta.get("base_model")
        or meta.get("model")
    )
    if v:
        return str(v)

    ckpt = _infer_checkpoint(meta)
    if ckpt and ckpt != "unknown":
        try:
            return Path(str(ckpt)).stem
        except Exception:
            return str(ckpt)

    return "unknown"


def _ksampler_params_from_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    k = meta.get("ksampler")
    if isinstance(k, dict):
        return k
    return {}


def _ksampler_params_from_graph(meta: Dict[str, Any]) -> Dict[str, Any]:
    try:
        graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
        for _, node in (graph or {}).items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") != "KSampler":
                continue
            inputs = node.get("inputs") or {}
            return {
                "sampler": inputs.get("sampler_name") or "",
                "scheduler": inputs.get("scheduler") or "",
                "steps": inputs.get("steps") or "",
                "cfg": inputs.get("cfg") or "",
                "denoise": inputs.get("denoise") or "",
            }
    except Exception:
        pass
    return {}


def _infer_combo_key(meta: Dict[str, Any], checkpoint: str) -> str:
    if not isinstance(meta, dict):
        return f"ckpt={checkpoint}"

    k = meta.get("combo_key")
    if k:
        return str(k)

    kp = _ksampler_params_from_meta(meta)
    sampler = kp.get("sampler") or meta.get("sampler") or ""
    scheduler = kp.get("scheduler") or meta.get("scheduler") or ""
    steps = kp.get("steps") or meta.get("steps") or ""
    cfg = kp.get("cfg") or meta.get("cfg") or ""
    denoise = kp.get("denoise") or meta.get("denoise") or ""

    if (not sampler or not scheduler or not steps or not cfg) and meta.get("chosen_line"):
        try:
            parts = [p.strip() for p in str(meta.get("chosen_line") or "").split(",")]
            if len(parts) >= 4:
                sampler = sampler or parts[0]
                scheduler = scheduler or parts[1]
                steps = steps or parts[2]
                cfg = cfg or parts[3]
        except Exception:
            pass

    if not sampler or not scheduler or not steps or not cfg or denoise == "":
        gp = _ksampler_params_from_graph(meta)
        sampler = sampler or gp.get("sampler") or ""
        scheduler = scheduler or gp.get("scheduler") or ""
        steps = steps or gp.get("steps") or ""
        cfg = cfg or gp.get("cfg") or ""
        denoise = denoise or gp.get("denoise") or ""

    return (
        f"ckpt={checkpoint}"
        f"|sampler={sampler}"
        f"|sched={scheduler}"
        f"|steps={steps}"
        f"|cfg={cfg}"
        f"|denoise={denoise}"
    )


def _build_item(png_path: Path, json_path: Path, root: Path) -> Item:
    meta = _safe_read_json(json_path)
    checkpoint = _infer_checkpoint(meta)
    model_branch = _infer_model_branch(meta)
    combo_key = _infer_combo_key(meta, checkpoint=checkpoint)
    subdir = _infer_subdir(png_path, root)

    return Item(
        png_path=png_path,
        json_path=json_path,
        subdir=subdir,
        model_branch=model_branch,
        checkpoint=checkpoint,
        combo_key=combo_key,
        meta=meta,
    )


def scan_output(root: Path, *, exts: Set[str] = {".png"}) -> List[Item]:
    items: List[Item] = []
    if not root.exists():
        return items

    for png_path in _iter_files_by_exts(root, exts):
        if not png_path.is_file():
            continue

        # vNext: ignore internal export folders under OUTPUT_ROOT
        # (we keep dataset copies there, but they must not become new review items)
        parts = {p.lower() for p in png_path.parts}
        if "_lora_export" in parts or "_trash" in parts:
            continue

        json_path = _sidecar_json_path(png_path)
        if not json_path.exists():
            continue

        items.append(_build_item(png_path, json_path, root))

    items.sort(key=lambda it: str(it.json_path))
    return items


def move_to_trash(output_root: Path, trash_root: Path, png_path: Path, json_path: Path) -> None:
    trash_root.mkdir(parents=True, exist_ok=True)
    try:
        rel = png_path.relative_to(output_root)
        dest_dir = trash_root / rel.parent
    except Exception:
        dest_dir = trash_root / png_path.parent.name
    dest_dir.mkdir(parents=True, exist_ok=True)

    shutil.move(str(png_path), str(dest_dir / png_path.name))
    shutil.move(str(json_path), str(dest_dir / json_path.name))