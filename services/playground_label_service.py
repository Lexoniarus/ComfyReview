"""Canonical prompt-label resolution for image presentation."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application import PromptCatalogService, PromptComponent

_SINGLE_KINDS = ("scene", "outfit", "pose", "expression")


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
    outfit_name: str
    pose_name: str
    expression_name: str
    modifiers: tuple[str, ...]
    light_name: str


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
        singles = {
            kind: self._first_match(candidates.get(kind, ()), prompt)
            for kind in _SINGLE_KINDS
        }
        lighting = (
            self._first_match(candidates.get("lighting", ()), prompt)
            if include_lighting
            else None
        )
        modifiers = self._matches(candidates.get("modifier", ()), prompt, 12)
        return PromptLabels(
            scene_name=self._name(singles["scene"]),
            outfit_name=self._name(singles["outfit"]),
            pose_name=self._name(singles["pose"]),
            expression_name=self._name(singles["expression"]),
            modifiers=tuple(label.name for label in modifiers if label.name),
            light_name=self._name(lighting),
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

    @classmethod
    def _matches(
        cls,
        candidates: tuple[PromptLabel, ...],
        prompt: str,
        limit: int,
    ) -> tuple[PromptLabel, ...]:
        return tuple(
            label
            for label in candidates
            if cls._normalize(label.positive_text) in prompt
        )[:limit]

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _name(label: PromptLabel | None) -> str:
        return label.name if label is not None else ""
