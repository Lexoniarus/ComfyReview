# services/comfy_client.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from config import COMFYUI_BASE_URL, WORKFLOWS_DIR, DEFAULT_WORKFLOW_PATH, COMFYUI_CHECKPOINTS_DIR

from services.comfy_client_core.discovery import get_checkpoints as _get_checkpoints
from services.comfy_client_core.discovery import get_samplers as _get_samplers
from services.comfy_client_core.discovery import get_schedulers as _get_schedulers
from services.comfy_client_core.http import http_json as _http_json
from services.comfy_client_core.patching import patch_workflow_for_run as _patch_workflow_for_run
from services.comfy_client_core.types import ComfyResponse
from services.comfy_client_core.workflows import get_or_create_workflow_path as _get_or_create_workflow_path
from services.comfy_client_core.workflows import load_workflow as _load_workflow


class ComfyClient:
    """Minimaler HTTP Client fuer ComfyUI ohne externe Dependencies.

    Wichtig
    - nutzt urllib (stdlib), kein requests
    - Workflows liegen in WORKFLOWS_DIR
    - Default Workflow wird als Fallback kopiert

    API: bewusst kompatibel zur vorherigen Version.
    Die Implementierung ist in services/comfy_client_core/ aufgeteilt.
    """

    def __init__(self, base_url: str = COMFYUI_BASE_URL, workflows_dir: Path = WORKFLOWS_DIR):
        self.base_url = str(base_url).rstrip("/")
        self.workflows_dir = Path(workflows_dir)

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
        timeout: int = 30,
    ) -> ComfyResponse:
        return _http_json(base_url=self.base_url, method=method, path=path, payload=payload, timeout=timeout)

    # ---------------------------------------------------------------------
    # Workflows
    # ---------------------------------------------------------------------

    def get_or_create_workflow_path(self, character_name: str) -> Path:
        return _get_or_create_workflow_path(
            workflows_dir=self.workflows_dir,
            character_name=character_name,
            default_workflow_path=Path(DEFAULT_WORKFLOW_PATH),
        )

    def load_workflow(self, path: Path) -> Dict[str, Any]:
        return _load_workflow(path)

    # ---------------------------------------------------------------------
    # Patching
    # ---------------------------------------------------------------------

    def patch_workflow_for_run(
        self,
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
        return _patch_workflow_for_run(
            workflow,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            subdir=subdir,
            checkpoint=checkpoint,
            seed=seed,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            denoise=denoise,
        )

    def enqueue_prompt(self, workflow: Dict[str, Any]) -> ComfyResponse:
        payload = {"prompt": workflow}
        return self._request_json("POST", "/prompt", payload=payload, timeout=60)

    def enqueue_from_playground(
        self,
        *,
        character_name: str,
        positive_prompt: str,
        negative_prompt: str,
        checkpoint: Optional[str] = None,
        seed: Optional[int] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        sampler: Optional[str] = None,
        scheduler: Optional[str] = None,
        denoise: Optional[float] = None,
        subdir: str = "playground",
    ) -> ComfyResponse:
        """Enqueue Playground job to ComfyUI."""
        try:
            if not character_name or not character_name.strip():
                return ComfyResponse(
                    ok=False,
                    status_code=400,
                    response_json={"error": "character_name is required"},
                    error="character_name is empty",
                )
            if not str(positive_prompt or "").strip() or not str(negative_prompt or "").strip():
                return ComfyResponse(
                    ok=False,
                    status_code=400,
                    response_json={"error": "positive and negative prompts required"},
                    error="prompts are empty",
                )

            workflow_path = self.get_or_create_workflow_path(character_name)
            workflow = self.load_workflow(workflow_path)

            workflow = self.patch_workflow_for_run(
                workflow,
                positive_prompt=str(positive_prompt or ""),
                negative_prompt=str(negative_prompt or ""),
                subdir=str(subdir or ""),
                checkpoint=checkpoint,
                seed=seed,
                steps=steps,
                cfg=cfg,
                sampler=sampler,
                scheduler=scheduler,
                denoise=denoise,
            )

            response = self.enqueue_prompt(workflow)

            if response.ok and response.response_json:
                if "prompt_id" in response.response_json:
                    response.response_json["_message"] = (
                        f"Successfully enqueued for character '{character_name}' "
                        f"[ID: {response.response_json['prompt_id']}]"
                    )
            return response

        except FileNotFoundError as e:
            return ComfyResponse(
                ok=False,
                status_code=404,
                response_json={"error": "Workflow not found"},
                error=str(e),
            )
        except Exception as e:
            return ComfyResponse(
                ok=False,
                status_code=500,
                response_json={"error": "Internal server error"},
                error=f"enqueue_from_playground failed: {str(e)}",
            )

    # ---------------------------------------------------------------------
    # Discovery (additiv)
    # ---------------------------------------------------------------------

    def get_samplers(self) -> list:
        return _get_samplers(self._request_json)

    def get_schedulers(self) -> list:
        return _get_schedulers(self._request_json)

    def get_checkpoints(self) -> list:
        return _get_checkpoints(self._request_json, checkpoints_dir=Path(COMFYUI_CHECKPOINTS_DIR))
