"""Read immutable versioned workflow blueprints from JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

from comfyreview.application import (
    WorkflowBlueprint,
    WorkflowCompilationError,
    WorkflowInputBinding,
    WorkflowOutputBinding,
)

_SAFE_UID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class JsonWorkflowBlueprintRepository:
    """Load explicit blueprint documents without legacy graph heuristics."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root).resolve()

    def get(
        self,
        blueprint_uid: str,
        version: int | None,
    ) -> WorkflowBlueprint:
        """Load a requested version or the latest available version."""
        uid = str(blueprint_uid or "").strip()
        if _SAFE_UID.fullmatch(uid) is None:
            raise WorkflowCompilationError("blueprint_uid is invalid")
        directory = (self._root / uid).resolve()
        if directory.parent != self._root:
            raise WorkflowCompilationError(
                "blueprint path escapes repository root"
            )
        selected_version = (
            self._latest_version(directory)
            if version is None
            else self._positive_version(version)
        )
        path = directory / f"v{selected_version}.json"
        if not path.is_file():
            raise KeyError(
                f"Unknown workflow blueprint: {uid} v{selected_version}"
            )
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise WorkflowCompilationError(
                "workflow blueprint JSON is invalid"
            ) from error
        if not isinstance(payload, dict):
            raise WorkflowCompilationError(
                "workflow blueprint must be an object"
            )
        return self._blueprint(
            cast(dict[str, Any], payload), uid, selected_version
        )

    @staticmethod
    def _latest_version(directory: Path) -> int:
        versions = [
            int(match.group(1))
            for path in directory.glob("v*.json")
            if (match := re.fullmatch(r"v([1-9][0-9]*)\.json", path.name))
        ]
        if not versions:
            raise KeyError(
                f"No workflow blueprint versions in {directory.name}"
            )
        return max(versions)

    @staticmethod
    def _positive_version(version: int) -> int:
        normalized = int(version)
        if normalized < 1:
            raise WorkflowCompilationError(
                "blueprint version must be positive"
            )
        return normalized

    @staticmethod
    def _blueprint(
        payload: dict[str, Any],
        expected_uid: str,
        expected_version: int,
    ) -> WorkflowBlueprint:
        if payload.get("blueprint_uid") != expected_uid:
            raise WorkflowCompilationError(
                "blueprint document identity does not match path"
            )
        if payload.get("version") != expected_version:
            raise WorkflowCompilationError(
                "blueprint document version does not match path"
            )
        graph = payload.get("graph")
        roles = payload.get("role_bindings")
        outputs = payload.get("output_bindings")
        sampler_roles = payload.get("sampler_roles")
        capabilities = payload.get("capability_requirements", [])
        if not isinstance(graph, dict) or not isinstance(roles, dict):
            raise WorkflowCompilationError(
                "blueprint graph or roles are invalid"
            )
        if not isinstance(outputs, list) or not isinstance(
            sampler_roles, list
        ):
            raise WorkflowCompilationError(
                "blueprint outputs or samplers are invalid"
            )
        if not isinstance(capabilities, list):
            raise WorkflowCompilationError(
                "blueprint capabilities are invalid"
            )
        try:
            role_bindings = {
                str(role): WorkflowInputBinding(
                    node_id=str(value["node_id"]),
                    input_name=str(value.get("input_name") or ""),
                )
                for role, value in roles.items()
                if isinstance(value, dict)
            }
            output_bindings = tuple(
                WorkflowOutputBinding(
                    role=str(value["role"]),
                    node_id=str(value["node_id"]),
                )
                for value in outputs
                if isinstance(value, dict)
            )
        except KeyError as error:
            raise WorkflowCompilationError(
                "blueprint binding is incomplete"
            ) from error
        if len(role_bindings) != len(roles) or len(output_bindings) != len(
            outputs
        ):
            raise WorkflowCompilationError(
                "blueprint binding entries are invalid"
            )
        return WorkflowBlueprint(
            blueprint_uid=expected_uid,
            version=expected_version,
            graph=cast(dict[str, Any], graph),
            role_bindings=role_bindings,
            output_bindings=output_bindings,
            sampler_roles=tuple(str(role) for role in sampler_roles),
            capability_requirements=tuple(
                str(value) for value in capabilities
            ),
        )
