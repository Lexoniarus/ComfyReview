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
from typing import Any, Dict, List, Set


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


# WAS TUT ES?
# Robust JSON lesen mit utf-8 und Fallback utf-8-sig.
# WO KOMMT ES HER?
# Sidecar JSON Datei aus name_meta_export.
# WO GEHT ES HIN?
# Dict meta geht in Inferenz Funktionen und ins Item.meta.
def _safe_read_json(p: Path) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}


# WAS TUT ES?
# Extrahiert checkpoint aus Meta.
# Erst direkt aus Meta Keys, dann aus comfy_prompt_graph Knoten.
# WO KOMMT ES HER?
# meta Dict aus Sidecar JSON.
# WO GEHT ES HIN?
# checkpoint wird in Item.checkpoint gesetzt und in combo_key verwendet und spaeter in der DB gespeichert.
def _infer_checkpoint(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return "unknown"
    ck = meta.get("checkpoint") or meta.get("ckpt_name") or meta.get("ckpt") or ""
    if ck:
        return str(ck)
    try:
        g = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
        for _, node in (g or {}).items():
            if isinstance(node, dict) and node.get("class_type") in ("CheckpointLoaderSimple", "CheckpointLoader"):
                inputs = node.get("inputs") or {}
                ck2 = inputs.get("ckpt_name") or inputs.get("checkpoint") or ""
                if ck2:
                    return str(ck2)
    except Exception:
        pass
    return "unknown"


# WAS TUT ES?
# Bestimmt model_branch fuer UI Filter.
# Bevorzugt meta["model_branch"] oder meta["model_base"] (dein Export Standard).
# Fallback ist Ableitung aus checkpoint Dateiname.
# WO KOMMT ES HER?
# meta Dict aus Sidecar JSON.
# WO GEHT ES HIN?
# model_branch wird in Item.model_branch gesetzt und spaeter in der DB gespeichert.
def _infer_model_branch(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return "unknown"

    v = (
        meta.get("model_branch")
        or meta.get("model_base")  # dein Standard Export-Key
        or meta.get("base_model")
        or meta.get("model")
    )
    if v:
        return str(v)

    # Fallback: aus checkpoint dateiname ableiten
    ckpt = _infer_checkpoint(meta)
    if ckpt and ckpt != "unknown":
        try:
            return Path(str(ckpt)).stem
        except Exception:
            return str(ckpt)

    return "unknown"


# WAS TUT ES?
# Erzeugt einen stabilen combo_key zum Gruppieren von Runs.
# Bevorzugt meta["combo_key"].
# Fallback ist ein String aus checkpoint plus KSampler Parametern.
# WO KOMMT ES HER?
# meta Dict aus Sidecar JSON und optional comfy_prompt_graph.
# WO GEHT ES HIN?
# combo_key wird in Item.combo_key gesetzt und spaeter in der DB gespeichert.
def _infer_combo_key(meta: Dict[str, Any], checkpoint: str) -> str:
    if not isinstance(meta, dict):
        return f"ckpt={checkpoint}"

    # bevorzugt view keys
    k = meta.get("combo_key")
    if k:
        return str(k)

    # attempt from comfy graph
    sampler = meta.get("sampler") or ""
    scheduler = meta.get("scheduler") or ""
    steps = meta.get("steps") or ""
    cfg = meta.get("cfg") or ""
    denoise = meta.get("denoise") or ""

    try:
        graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
        for _, node in (graph or {}).items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") != "KSampler":
                continue
            inputs = node.get("inputs") or {}
            sampler = sampler or inputs.get("sampler_name") or ""
            scheduler = scheduler or inputs.get("scheduler") or ""
            steps = steps or inputs.get("steps") or ""
            cfg = cfg or inputs.get("cfg") or ""
            denoise = denoise or inputs.get("denoise") or ""
            break
    except Exception:
        pass

    return f"ckpt={checkpoint}|sampler={sampler}|sched={scheduler}|steps={steps}|cfg={cfg}|denoise={denoise}"


# WAS TUT ES?
# Scannt rekursiv im Output Root nach PNGs und erwartet eine Sidecar JSON mit identischem Basisnamen.
# Baut Item Objekte und sortiert stabil nach json_path.
# WO KOMMT ES HER?
# root ist OUTPUT_ROOT aus config.
# WO GEHT ES HIN?
# Items gehen an Router oder Service, zB fuer index Ansicht oder DB inserts.
def scan_output(root: Path, *, exts: Set[str] = {".png"}) -> List[Item]:
    items: List[Item] = []
    if not root.exists():
        return items

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue

        png_path = p
        json_path = p.with_suffix(".json")
        if not json_path.exists():
            continue

        meta = _safe_read_json(json_path)
        checkpoint = _infer_checkpoint(meta)
        model_branch = _infer_model_branch(meta)
        combo_key = _infer_combo_key(meta, checkpoint=checkpoint)

        # subdir relativ zu output root
        try:
            subdir = str(png_path.parent.relative_to(root))
        except Exception:
            subdir = str(png_path.parent.name)

        items.append(
            Item(
                png_path=png_path,
                json_path=json_path,
                subdir=subdir,
                model_branch=model_branch,
                checkpoint=checkpoint,
                combo_key=combo_key,
                meta=meta,
            )
        )

    # sort stabil
    items.sort(key=lambda it: str(it.json_path))
    return items


# WAS TUT ES?
# Verschiebt PNG und JSON in einen Trash Ordner.
# Wichtig: Das ist nur Dateisystem Handling.
# Das DB deleted Flag Handling passiert separat im Review Tool.
# WO KOMMT ES HER?
# Aufruf aus Service Layer, wenn User Delete ausloest.
# WO GEHT ES HIN?
# Dateien landen unter trash_root und behalten die Ordnerstruktur relativ zu output_root.
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