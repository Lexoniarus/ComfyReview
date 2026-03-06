# meta_view.py
#
# WAS IST DAS?
# Reiner View Layer fuer Meta Daten.
# Nimmt das raw Meta JSON (aus Sidecar JSON neben dem PNG) und baut eine UI freundliche Sicht darauf.
# Dabei werden Werte bevorzugt aus comfy_prompt_graph gezogen, weil das die genaueste Quelle ist.
# Falls kein Graph vorhanden ist, werden gespeicherte Meta Keys genutzt.
#
# WO KOMMT ES HER?
# Input meta kommt aus:
# - Sidecar JSON Datei, die name_meta_export schreibt
# - oder aus DB gespeicherten Meta Feldern, die aus dieser JSON stammen
#
# WO GEHT ES HIN?
# Output view Dict geht an:
# - Template Rendering (meta/prompt Ansicht)
# - Router Responses
# preset_text_from_view liefert Text fuer UI Preset Felder
# extract_prompts liefert pos/neg plus einen Hinweistext fuer UI
#
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional, Tuple


# WAS IST DAS?
# Kleine View Struktur fuer LoRA Eintraege.
# name ist der LoRA Filename.
# sm sc sind strength_model und strength_clip.
@dataclass
class LoRAView:
    name: str
    sm: Optional[float] = None
    sc: Optional[float] = None


# WAS IST DAS?
# Regex Muster, die einen Prompt Wrapper entfernen.
# Das sind fixe Texte, die in manchen Meta Exports vor dem Prompt landen.
_PROMPT_WRAPPER_PATTERNS = [
    r"^You are an assistant designed to generate high quality anime images based on textual prompts\.?\s*",
    r"^You are an assistant designed to generate low-quality images based on textual prompts\.?\s*",
    r"^<\s*Prompt\s*Start\s*>\s*",
]


# WAS TUT ES?
# Entfernt bekannte Wrapper aus Prompt Text und trimmt Whitespace.
# WO KOMMT ES HER?
# text kommt aus comfy_prompt_graph Prompt Extraction oder aus meta pos_prompt/neg_prompt Keys.
# WO GEHT ES HIN?
# Clean Prompt Text geht in view["pos_prompt"] / view["neg_prompt"].
def _clean_prompt_text(text: str) -> str:
    if not text:
        return ""
    t = str(text).strip()
    for pat in _PROMPT_WRAPPER_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE | re.MULTILINE)
    t = re.sub(r"^\s*\n+", "", t, flags=re.MULTILINE)
    return t.strip()


# WAS TUT ES?
# Rein Convenience: pos und neg beide reinigen.
# WO KOMMT ES HER?
# pos neg kommen aus _extract_prompts_via_ksampler oder aus meta keys.
# WO GEHT ES HIN?
# Gereinigte Prompts gehen in view.
def _clean_prompts(pos: str, neg: str) -> Tuple[str, str]:
    return _clean_prompt_text(pos), _clean_prompt_text(neg)


# WAS TUT ES?
# Findet den ersten KSampler Node im comfy_prompt_graph und gibt ihn zurueck.
# WO KOMMT ES HER?
# meta enthält comfy_prompt_graph oder prompt_graph.
# WO GEHT ES HIN?
# Inputs aus dem Node werden genutzt um seed steps cfg sampler scheduler denoise zu befuellen.
def _ksampler_from_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if not isinstance(graph, dict):
        return {}

    for _, node in graph.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "KSampler":
            return node
    return {}


# WAS TUT ES?
# Extrahiert Checkpoint Name.
# Erst versucht es direkte Meta Keys, danach sucht es im comfy_prompt_graph nach CheckpointLoader Nodes.
# WO KOMMT ES HER?
# meta aus Sidecar JSON.
# WO GEHT ES HIN?
# view["checkpoint"].
def _extract_ckpt(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return ""

    # direct
    for k in ("checkpoint", "ckpt_name", "ckpt"):
        if meta.get(k):
            return str(meta.get(k))

    # comfy graph
    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if isinstance(graph, dict):
        for _, node in graph.items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") in ("CheckpointLoaderSimple", "CheckpointLoader", "RandomLoadCheckpoint", "RandomLoadCheckpointSimple"):
                inputs = node.get("inputs") or {}
                ck = inputs.get("ckpt_name") or inputs.get("checkpoint") or ""
                if ck:
                    return str(ck)

    return ""


# WAS TUT ES?
# Extrahiert Bildaufloesung.
# Erst width/height aus Meta Keys, dann aus comfy_prompt_graph ueber EmptyLatentImage Nodes.
# WO KOMMT ES HER?
# meta aus Sidecar JSON.
# WO GEHT ES HIN?
# view["resolution"] als String "WxH".
def _extract_resolution(meta: Dict[str, Any]) -> str:
    if not isinstance(meta, dict):
        return ""

    w = meta.get("width")
    h = meta.get("height")
    if w and h:
        return f"{w}x{h}"

    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if isinstance(graph, dict):
        for _, node in graph.items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") in ("EmptyLatentImage", "EmptySD3LatentImage"):
                inputs = node.get("inputs") or {}
                w = inputs.get("width")
                h = inputs.get("height")
                if w and h:
                    return f"{w}x{h}"

    return ""


# WAS TUT ES?
# Extrahiert LoRAs aus comfy_prompt_graph ueber LoraLoader Nodes.
# WO KOMMT ES HER?
# meta["comfy_prompt_graph"] oder meta["prompt_graph"].
# WO GEHT ES HIN?
# view["loras"] als Liste von LoRAView.
def _extract_loras(meta: Dict[str, Any]) -> List[LoRAView]:
    out: List[LoRAView] = []
    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if not isinstance(graph, dict):
        return out

    for _, node in graph.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != "LoraLoader":
            continue
        inputs = node.get("inputs") or {}
        name = inputs.get("lora_name")
        if not name:
            continue
        sm = inputs.get("strength_model")
        sc = inputs.get("strength_clip")
        try:
            sm = float(sm) if sm is not None else None
        except Exception:
            sm = None
        try:
            sc = float(sc) if sc is not None else None
        except Exception:
            sc = None
        out.append(LoRAView(name=str(name), sm=sm, sc=sc))
    return out


# WAS TUT ES?
# Extrahiert pos und neg Prompt Text durch Aufloesen der Verknuepfungen am KSampler:
# KSampler.inputs.positive und negative sind Refs auf andere Nodes.
# resolve_text verfolgt diese Referenzen und baut den finalen String.
#
# WO KOMMT ES HER?
# graph kommt aus meta["comfy_prompt_graph"].
#
# WO GEHT ES HIN?
# pos neg gehen in view und werden danach noch gereinigt.
def _extract_prompts_via_ksampler(graph: Dict[str, Any]) -> Tuple[str, str]:
    if not isinstance(graph, dict):
        return "", ""

    ksam = None
    for _, node in graph.items():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            ksam = node
            break
    if not ksam:
        return "", ""

    inputs = ksam.get("inputs") or {}
    pos_ref = inputs.get("positive")
    neg_ref = inputs.get("negative")

    def resolve_text(ref: Any) -> str:
        # WAS TUT ES?
        # Loest einen ComfyUI Node Ref der Form [node_id, output_index] auf.
        #
        # WO KOMMT ES HER?
        # ref kommt aus KSampler.inputs.positive oder negative.
        #
        # WO GEHT ES HIN?
        # Gibt einen finalen String zurueck, der Prompt Text repraesentiert.
        if not ref or not isinstance(ref, list) or len(ref) < 2:
            return ""
        node_id = str(ref[0])
        node = graph.get(node_id)
        if not isinstance(node, dict):
            return ""
        inps = node.get("inputs") or {}

        # CLIPTextEncode kann text als ref speichern, also weiter aufloesen
        if "text" in inps and isinstance(inps["text"], list):
            return resolve_text(inps["text"])

        # Primitive String Nodes speichern im Normalfall value
        if "value" in inps:
            return str(inps.get("value") or "")

        # Manche Nodes bauen Strings aus zwei Inputs zusammen
        if "string_a" in inps and "string_b" in inps:
            a = resolve_text(inps.get("string_a"))
            b = resolve_text(inps.get("string_b"))
            delim = str(inps.get("delimiter") or "")
            return f"{a}{delim}{b}"

        # Fallback: text direkt als string
        if "text" in inps and isinstance(inps["text"], str):
            return str(inps["text"])

        return ""

    pos = resolve_text(pos_ref)
    neg = resolve_text(neg_ref)
    return pos, neg


# WAS TUT ES?
# Hauptfunktion: baut ein View Dict aus raw meta.
# Bevorzugt comfy_prompt_graph fuer ksampler und prompts, sonst fallback auf gespeicherte meta keys.
#
# WO KOMMT ES HER?
# meta kommt aus Sidecar JSON (name_meta_export) oder gespeicherten Meta Keys.
#
# WO GEHT ES HIN?
# view geht an Templates, Router Responses und UI.
def extract_view(meta: Dict[str, Any]) -> Dict[str, Any]:
    view: Dict[str, Any] = {}

    view["checkpoint"] = _extract_ckpt(meta)
    view["resolution"] = _extract_resolution(meta)

    # ksampler direct keys
    ksam = _ksampler_from_meta(meta)
    inputs = (ksam.get("inputs") or {}) if isinstance(ksam, dict) else {}

    view["seed"] = inputs.get("seed") or meta.get("seed")
    view["steps"] = inputs.get("steps") or meta.get("steps")
    view["cfg"] = inputs.get("cfg") or meta.get("cfg")
    view["sampler"] = inputs.get("sampler_name") or meta.get("sampler")
    view["scheduler"] = inputs.get("scheduler") or meta.get("scheduler")
    view["denoise"] = inputs.get("denoise") or meta.get("denoise")

    # prompts
    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if isinstance(graph, dict) and graph:
        view["pos_prompt"], view["neg_prompt"] = _extract_prompts_via_ksampler(graph)
        view["pos_prompt"], view["neg_prompt"] = _clean_prompts(view["pos_prompt"], view["neg_prompt"])
    else:
        view["pos_prompt"] = str(meta.get("pos_prompt") or "")
        view["neg_prompt"] = str(meta.get("neg_prompt") or "")
        view["pos_prompt"], view["neg_prompt"] = _clean_prompts(view["pos_prompt"], view["neg_prompt"])

    # loras
    view["loras"] = _extract_loras(meta)
    return view


# WAS TUT ES?
# Baut ein kurzes Preset String Format fuer UI Felder.
# Format: sampler,scheduler,steps
# WO KOMMT ES HER?
# view Dict aus extract_view.
# WO GEHT ES HIN?
# UI Preset Anzeige.
def preset_text_from_view(view: Dict[str, Any]) -> str:
    sampler = str(view.get("sampler") or "")
    scheduler = str(view.get("scheduler") or "")
    steps = str(view.get("steps") or "")
    return f"{sampler},{scheduler},{steps}"


# WAS TUT ES?
# Liefert pos neg Prompt plus Info Text, ob Prompts aus Graph oder aus Meta Keys kamen.
# WO KOMMT ES HER?
# meta aus Sidecar JSON.
# WO GEHT ES HIN?
# Router Response oder Template Prompt Ansicht.
def extract_prompts(meta: Dict[str, Any]) -> Tuple[str, str, str]:
    graph = meta.get("comfy_prompt_graph") or meta.get("prompt_graph") or {}
    if isinstance(graph, dict) and graph:
        pos, neg = _extract_prompts_via_ksampler(graph)
        pos, neg = _clean_prompts(pos, neg)
        return pos, neg, "Prompts filled from comfy_prompt_graph (server-side)."

    pos = str(meta.get("pos_prompt") or "")
    neg = str(meta.get("neg_prompt") or "")
    pos, neg = _clean_prompts(pos, neg)
    return pos, neg, "Prompts filled from stored meta keys."