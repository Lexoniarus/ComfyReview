# services/comfy_client.py
#
# WAS IST DAS?
# Client fuer ComfyUI HTTP API.
# Wird von Routern/Services genutzt, um:
# - Optionen (Checkpoints, Sampler, Scheduler) zu entdecken
# - Workflows (JSON) zu laden/initialisieren
# - Workflows zu patchen (Prompts, Parameter, Subdir)
# - Prompt Jobs in ComfyUI Queue einzureihen
#
# WICHTIG
# - Diese Datei aendert NICHT dein Output JSON Schema.
# - Wir patchen nur den Workflow Input fuer ComfyUI, damit name_meta_export weiterhin exakt gleich exportiert.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import os

import requests

from config import (
    COMFYUI_BASE_URL,
    WORKFLOWS_DIR,
    DEFAULT_WORKFLOW_PATH,
    COMFYUI_CHECKPOINTS_DIR,
)

JsonDict = Dict[str, Any]


@dataclass
class ComfyEnqueueResult:
    ok: bool
    status_code: int
    response_json: JsonDict
    error: str = ""


class ComfyClient:
    def __init__(self, base_url: str = COMFYUI_BASE_URL, timeout_s: int = 30):
        self.base_url = str(base_url).rstrip("/")
        self.timeout_s = int(timeout_s)

        self.workflows_dir = Path(WORKFLOWS_DIR)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        self.default_workflow_path = Path(DEFAULT_WORKFLOW_PATH)

    # ---------------------------------------------------------------------
    # Discovery
    # ---------------------------------------------------------------------

    def discover_samplers_and_schedulers(self) -> Tuple[List[str], List[str]]:
        url = f"{self.base_url}/object_info"
        r = requests.get(url, timeout=self.timeout_s)
        r.raise_for_status()
        payload = r.json()

        ks = payload.get("KSampler") or {}
        inputs = ks.get("input") or {}
        required = inputs.get("required") or {}

        samplers = []
        schedulers = []

        s = required.get("sampler_name")
        if isinstance(s, list) and s:
            samplers = list(s[0]) if isinstance(s[0], list) else list(s)

        sc = required.get("scheduler")
        if isinstance(sc, list) and sc:
            schedulers = list(sc[0]) if isinstance(sc[0], list) else list(sc)

        return samplers, schedulers

    def discover_checkpoints(self) -> List[str]:
        base = Path(COMFYUI_CHECKPOINTS_DIR)
        if not base.exists():
            return []

        out = []
        for ext in (".safetensors", ".ckpt", ".pt"):
            out.extend([p.name for p in base.glob(f"*{ext}") if p.is_file()])
        out = sorted(set(out))
        return out

    # ---------------------------------------------------------------------
    # Workflow IO
    # ---------------------------------------------------------------------

    def get_or_create_workflow_path(self, character_name: str) -> Path:
        safe = str(character_name or "").strip()
        if safe:
            p = self.workflows_dir / f"{safe}.json"
            if p.exists():
                return p

            if self.default_workflow_path.exists():
                p.write_text(self.default_workflow_path.read_text(encoding="utf-8"), encoding="utf-8")
                return p

        return self.default_workflow_path

    def load_workflow(self, workflow_path: Path) -> JsonDict:
        p = Path(workflow_path)
        if not p.exists():
            raise FileNotFoundError(f"workflow nicht gefunden: {p}")
        return json.loads(p.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------------
    # Patch
    # ---------------------------------------------------------------------

    def patch_workflow_for_run(
        self,
        workflow: JsonDict,
        *,
        positive_prompt: str,
        negative_prompt: str,
        subdir: str,
        checkpoint_list: List[str],
        sampler_list: List[str],
        scheduler_list: List[str],
        steps_min: int,
        steps_max: int,
        cfg_min: float,
        cfg_max: float,
        cfg_step: float,
        auto_increment: bool,
        max_runs: int,
        shuffle_order: bool,
        fixed_shuffle_seed: int,
        seed: int,
        control_after_generate: str,
    ) -> JsonDict:
        """
        Patcht einen ComfyUI Workflow so, dass er genau unsere ComfyReview Inputs nutzt.

        Garantien:
        - chosen_line bleibt korrekt, weil RandomSamplerSchedulerSteps weiterhin Source-of-Truth ist
        - name_meta_export bleibt unberuehrt, nur subdir wird gesetzt
        - Positive/Negative Prompt landen genau in den Nodes, die in KSampler verlinkt sind

        Hinweis:
        - Wir patchen ueber Links, nicht ueber feste Node IDs.
        """
        wf = json.loads(json.dumps(workflow))  # deep copy
        nodes = wf.get("nodes") or []
        links = wf.get("links") or []

        node_by_id: Dict[int, JsonDict] = {}
        for n in nodes:
            try:
                node_by_id[int(n.get("id"))] = n
            except Exception:
                continue

        def _find_first_node_id_by_type(t: str) -> Optional[int]:
            for n in nodes:
                if n.get("type") == t:
                    try:
                        return int(n.get("id"))
                    except Exception:
                        return None
            return None

        def _link_by_id(lid: int) -> Optional[list]:
            for l in links:
                if isinstance(l, list) and l and int(l[0]) == int(lid):
                    return l
            return None

        def _source_node_for_target_input(target_node_id: int, target_input_idx: int) -> Optional[int]:
            tnode = node_by_id.get(int(target_node_id))
            if not tnode:
                return None
            ins = tnode.get("inputs") or []
            if target_input_idx >= len(ins):
                return None
            link_id = ins[target_input_idx].get("link")
            if link_id is None:
                return None
            l = _link_by_id(int(link_id))
            if not l:
                return None
            try:
                return int(l[1])
            except Exception:
                return None

        # 1) Prompts: ueber KSampler Verlinkung
        ks_id = _find_first_node_id_by_type("KSampler")
        if ks_id is None:
            raise RuntimeError("Workflow Patch: KSampler nicht gefunden")

        # KSampler Inputs Reihenfolge im Export:
        # 0 model, 1 positive, 2 negative, 3 latent, ...
        pos_src_id = _source_node_for_target_input(ks_id, 1)
        neg_src_id = _source_node_for_target_input(ks_id, 2)
        if pos_src_id is None or neg_src_id is None:
            raise RuntimeError("Workflow Patch: positive/negative Source Nodes nicht gefunden")

        for nid, txt in ((pos_src_id, positive_prompt), (neg_src_id, negative_prompt)):
            n = node_by_id.get(int(nid))
            if not n:
                continue
            wv = n.get("widgets_values")
            if not isinstance(wv, list):
                wv = []
                n["widgets_values"] = wv
            if not wv:
                wv.append("")
            wv[0] = str(txt)

        # 2) Subdir: name_meta_export widget[0]
        nme_id = _find_first_node_id_by_type("name_meta_export")
        if nme_id is None:
            raise RuntimeError("Workflow Patch: name_meta_export nicht gefunden")

        nme = node_by_id.get(int(nme_id))
        wv = nme.get("widgets_values")
        if not isinstance(wv, list):
            wv = []
            nme["widgets_values"] = wv
        while len(wv) < 1:
            wv.append("")
        wv[0] = str(subdir)

        # 3) RandomSamplerSchedulerSteps: Source-of-Truth befuellen
        rss_id = _find_first_node_id_by_type("RandomSamplerSchedulerSteps")
        if rss_id is None:
            raise RuntimeError("Workflow Patch: RandomSamplerSchedulerSteps nicht gefunden")

        rss = node_by_id.get(int(rss_id))
        wv = rss.get("widgets_values")
        if not isinstance(wv, list):
            wv = []
            rss["widgets_values"] = wv

        def _ensure_len(n: int) -> None:
            while len(wv) < n:
                wv.append(None)

        # neue Version (14):
        # 0 checkpoint_list,1 samplers,2 schedulers,3 steps_min,4 steps_max,5 cfg_min,6 cfg_max,7 cfg_step,
        # 8 auto_increment,9 max_runs,10 shuffle_order,11 fixed_shuffle_seed,12 seed,13 control_after_generate
        #
        # alte Version (15): wie oben, plus seed_mode vor control_after_generate
        if len(wv) >= 15:
            _ensure_len(15)
            idx_control = 14
            idx_seed_mode = 13
        else:
            _ensure_len(14)
            idx_control = 13
            idx_seed_mode = None

        wv[0] = "\n".join([str(x) for x in checkpoint_list if str(x).strip()]) + "\n"
        wv[1] = "\n".join([str(x) for x in sampler_list if str(x).strip()]) if sampler_list else "ALL"
        wv[2] = "\n".join([str(x) for x in scheduler_list if str(x).strip()]) if scheduler_list else "ALL"
        wv[3] = int(steps_min)
        wv[4] = int(steps_max)
        wv[5] = float(cfg_min)
        wv[6] = float(cfg_max)
        wv[7] = float(cfg_step)
        wv[8] = bool(auto_increment)
        wv[9] = int(max_runs)
        wv[10] = bool(shuffle_order)
        wv[11] = int(fixed_shuffle_seed)
        wv[12] = int(seed)

        if idx_seed_mode is not None:
            wv[idx_seed_mode] = str(control_after_generate)
        wv[idx_control] = str(control_after_generate)

        return wf

    # ---------------------------------------------------------------------
    # Playground Bridge
    # ---------------------------------------------------------------------
    #
    # Ziel
    # - Router soll nur noch character_name plus prompts liefern
    # - ComfyClient kuemmert sich um:
    #   - Workflow Auswahl (pro Character oder Default)
    #   - Discovery (Checkpoints, Sampler, Scheduler)
    #   - Patch (Prompts, Subdir, RSS Inputs)
    #   - Enqueue (POST /prompt)
    #
    # Wichtig
    # - Keine Aenderung am bestehenden Review JSON Schema
    # - RandomSamplerSchedulerSteps bleibt Source-of-Truth (chosen_line bleibt korrekt)
    #
    def enqueue_from_playground(
        self,
        *,
        character_name: str,
        positive_prompt: str,
        negative_prompt: str,
        seed: Optional[int] = None,
    ) -> ComfyEnqueueResult:
        """
        Convenience Wrapper fuer Playground Submit.

        Parameter
        - character_name: bestimmt Workflow Datei und Subdir
        - positive_prompt, negative_prompt: werden in die Text Nodes injiziert, die am KSampler haengen
        - seed: wird an RandomSamplerSchedulerSteps (seed) uebergeben. Wenn None, wird 0 genutzt.

        Defaults (wie RandomSamplerSchedulerSteps Node Defaults)
        - steps_min 15, steps_max 35
        - cfg_min 4.0, cfg_max 9.0, cfg_step 0.5
        - auto_increment True, max_runs 0
        - shuffle_order True, fixed_shuffle_seed 0
        - control_after_generate "fixed"
        """
        wf_path = self.get_or_create_workflow_path(character_name=character_name)
        wf = self.load_workflow(wf_path)

        # Discovery
        ckpts = self.discover_checkpoints()
        samplers, schedulers = self.discover_samplers_and_schedulers()

        # Checkpoints muessen explizit rein, sonst ist RSS leer.
        # Sampler und Scheduler koennen als "ALL" laufen, wenn Listen leer sind.
        checkpoint_list = ckpts
        sampler_list = []
        scheduler_list = []

        patched = self.patch_workflow_for_run(
            wf,
            positive_prompt=str(positive_prompt or ""),
            negative_prompt=str(negative_prompt or ""),
            subdir=str(character_name or "output"),
            checkpoint_list=checkpoint_list,
            sampler_list=sampler_list,
            scheduler_list=scheduler_list,
            steps_min=15,
            steps_max=35,
            cfg_min=4.0,
            cfg_max=9.0,
            cfg_step=0.5,
            auto_increment=True,
            max_runs=0,
            shuffle_order=True,
            fixed_shuffle_seed=0,
            seed=int(seed or 0),
            control_after_generate="fixed",
        )

        return self.enqueue_prompt(patched)

    # ---------------------------------------------------------------------
    # Enqueue
    # ---------------------------------------------------------------------

    def enqueue_prompt(self, workflow: JsonDict) -> ComfyEnqueueResult:
        url = f"{self.base_url}/prompt"
        try:
            r = requests.post(url, json={"prompt": workflow}, timeout=self.timeout_s)
            try:
                payload = r.json()
            except Exception:
                payload = {"text": r.text}

            ok = 200 <= int(r.status_code) < 300
            return ComfyEnqueueResult(
                ok=ok,
                status_code=int(r.status_code),
                response_json=payload,
                error="" if ok else str(payload),
            )
        except Exception as e:
            return ComfyEnqueueResult(ok=False, status_code=0, response_json={}, error=str(e))

    # ---------------------------------------------------------------------
    # Helper
    # ---------------------------------------------------------------------

    def _get_json(self, url: str) -> JsonDict:
        r = requests.get(url, timeout=self.timeout_s)
        r.raise_for_status()
        return r.json()