"""Canonical prompt-label resolution for image presentation."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application import PromptCatalogService, PromptComponent
from comfyreview.application.prompt_kinds import OPTIONAL_PROMPT_KINDS

_DISPLAY_KINDS = OPTIONAL_PROMPT_KINDS


@dataclass(frozen=True, slots=True)
class PromptLabel:
    """Describe one catalog component detected in a rendered prompt."""

    kind: str
    name: str
    component_key: str
    positive_text: str


@dataclass(frozen=True, slots=True)
class PromptLabels:
    """Contain the catalog labels displayed for one image prompt."""

    scene_name: str
    atmosphere_name: str
    light_name: str
    outfit_name: str
    accessory_name: str
    pose_name: str
    expression_name: str
    framing_name: str
    camera_angle_name: str
    optical_effect_name: str


class PromptLabelService:
    """Resolve display labels from active canonical prompt revisions."""

    def __init__(self, catalog: PromptCatalogService) -> None:
        self._catalog = catalog

    def resolve(
        self,
        positive_prompt: str,
        *,
        include_lighting: bool = True,
    ) -> PromptLabels:
        """Return the longest matching labels for one positive prompt."""
        prompt = self._normalize(positive_prompt)
        candidates = self._candidates(
            self._catalog.list_components(include_archived=False)
        )
        matches = {
            kind: self._first_match(candidates.get(kind, ()), prompt)
            for kind in _DISPLAY_KINDS
        }
        if not include_lighting:
            matches["lighting"] = None
        return PromptLabels(
            scene_name=self._name(matches["scene"]),
            atmosphere_name=self._name(matches["atmosphere"]),
            light_name=self._name(matches["lighting"]),
            outfit_name=self._name(matches["outfit"]),
            accessory_name=self._name(matches["accessory"]),
            pose_name=self._name(matches["pose"]),
            expression_name=self._name(matches["expression"]),
            framing_name=self._name(matches["framing"]),
            camera_angle_name=self._name(matches["camera_angle"]),
            optical_effect_name=self._name(matches["optical_effect"]),
        )

    @classmethod
    def _candidates(
        cls,
        components: tuple[PromptComponent, ...],
    ) -> dict[str, tuple[PromptLabel, ...]]:
        grouped: dict[str, list[PromptLabel]] = {}
        for component in components:
            positive_text = component.standard_revision.positive_text.strip()
            if not positive_text:
                continue
            grouped.setdefault(component.kind, []).append(
                PromptLabel(
                    kind=component.kind,
                    name=component.name,
                    component_key=component.component_key,
                    positive_text=positive_text,
                )
            )
        return {
            kind: tuple(
                sorted(
                    labels,
                    key=lambda label: len(cls._normalize(label.positive_text)),
                    reverse=True,
                )
            )
            for kind, labels in grouped.items()
        }

    @classmethod
    def _first_match(
        cls,
        candidates: tuple[PromptLabel, ...],
        prompt: str,
    ) -> PromptLabel | None:
        return next(
            (
                label
                for label in candidates
                if cls._normalize(label.positive_text) in prompt
            ),
            None,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _name(label: PromptLabel | None) -> str:
        return label.name if label is not None else ""
